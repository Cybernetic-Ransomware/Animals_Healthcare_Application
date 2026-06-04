from datetime import date as _date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from ahc.apps.medical_notes.models.type_measurement_notes import (
    BiometricHeightRecords,
    BiometricWeightRecords,
)
from ahc.apps.medical_notes.selectors import (
    can_access_note_animal,
    is_attachment_author,
    is_author_of_any_note,
    is_note_author,
)
from ahc.apps.medical_notes.services.attachments import (
    AttachmentLimitExceeded,
    delete_attachment,
    download_attachment,
    upload_attachment,
)
from ahc.apps.medical_notes.services.notes import create_note, next_route_for, update_note
from ahc.apps.medical_notes.services.notifications import create_email_notification
from ahc.apps.medical_notes.signals.type_measurement_notes import validate_one_to_one_fields
from ahc.apps.medical_notes.utils import build_timeline_base_query


def _make_instance(weight=None, height=None, custom=None):
    instance = MagicMock()
    instance.weight_biometric_record = weight
    instance.height_biometric_record = height
    instance.custom_biometric_record = custom
    return instance


@pytest.mark.unit
class TestBiometricRecordValidation:
    """validate_one_to_one_fields: at most one measurement type per BiometricRecord."""

    def test_two_types_raises_validation_error(self):
        instance = _make_instance(
            weight=BiometricWeightRecords(weight=5),
            height=BiometricHeightRecords(height=30),
        )
        with pytest.raises(ValidationError):
            validate_one_to_one_fields(sender=None, instance=instance)

    def test_all_three_types_raises_validation_error(self):
        from ahc.apps.medical_notes.models.type_measurement_notes import BiometricCustomRecords

        instance = _make_instance(
            weight=BiometricWeightRecords(weight=5),
            height=BiometricHeightRecords(height=30),
            custom=BiometricCustomRecords(record_name="x", record_value="1", record_unit="cm"),
        )
        with pytest.raises(ValidationError):
            validate_one_to_one_fields(sender=None, instance=instance)

    def test_weight_only_is_valid(self):
        instance = _make_instance(weight=BiometricWeightRecords(weight=5))
        validate_one_to_one_fields(sender=None, instance=instance)

    def test_height_only_is_valid(self):
        instance = _make_instance(height=BiometricHeightRecords(height=30))
        validate_one_to_one_fields(sender=None, instance=instance)

    def test_all_none_is_valid(self):
        instance = _make_instance()
        validate_one_to_one_fields(sender=None, instance=instance)


def _make_couch_client(save_ok=True, get_result=None, delete_ok=True):
    """Build a mock CouchAttachmentClient for attachment service tests."""
    client = MagicMock()
    client.save_attachment.return_value = "ref-uuid"
    client.delete_attachment.return_value = None
    client.get_attachment.return_value = get_result
    return client


@pytest.mark.unit
class TestUploadAttachmentService:
    """upload_attachment: orchestrates limit check, CouchDB write, and model save."""

    def test_raises_when_limit_reached(self):
        medical_record = MagicMock()
        attachment = MagicMock()
        uploaded_file = BytesIO(b"data")
        uploaded_file.name = "photo.jpg"
        client = _make_couch_client()

        with (
            patch("ahc.apps.medical_notes.services.attachments.MedicalRecordAttachment.objects.filter") as mock_filter,
            patch("ahc.apps.medical_notes.services.attachments.settings") as mock_settings,
        ):
            mock_settings.COUCH_DB_LIMIT_PER_NOTE = 5
            mock_filter.return_value.count.return_value = 5

            with pytest.raises(AttachmentLimitExceeded):
                upload_attachment(medical_record, attachment, uploaded_file, couch_client=client)

        client.save_attachment.assert_not_called()

    def test_saves_to_couch_and_model_when_under_limit(self):
        medical_record = MagicMock()
        attachment = MagicMock()
        attachment.id = "test-uuid"
        uploaded_file = BytesIO(b"image-data")
        uploaded_file.name = "photo.jpg"
        client = _make_couch_client()

        with (
            patch("ahc.apps.medical_notes.services.attachments.MedicalRecordAttachment.objects.filter") as mock_filter,
            patch("ahc.apps.medical_notes.services.attachments.settings") as mock_settings,
            patch("ahc.apps.medical_notes.services.attachments.transaction"),
        ):
            mock_settings.COUCH_DB_LIMIT_PER_NOTE = 5
            mock_filter.return_value.count.return_value = 2

            result = upload_attachment(medical_record, attachment, uploaded_file, couch_client=client)

        client.save_attachment.assert_called_once_with("test-uuid", "photo.jpg", b"image-data")
        assert attachment.couch_id == "test-uuid"
        assert attachment.file_name == "photo.jpg"
        assert attachment.file is None
        assert result is attachment


@pytest.mark.unit
class TestDeleteAttachmentService:
    """delete_attachment: calls couch client then deletes the model row."""

    def test_deletes_from_couch_and_db(self):
        attachment = MagicMock()
        attachment.couch_id = "some-couch-id"
        client = _make_couch_client()

        delete_attachment(attachment, couch_client=client)

        client.delete_attachment.assert_called_once_with("some-couch-id")
        attachment.delete.assert_called_once()


@pytest.mark.unit
class TestDownloadAttachmentService:
    """download_attachment: retrieves bytes from couch client; raises Http404 on missing."""

    def test_returns_bytes_and_name(self):
        client = _make_couch_client(get_result=({"name": "report.pdf"}, b"pdf-bytes"))

        file_data, file_name = download_attachment("ref-uuid", couch_client=client)

        assert file_data == b"pdf-bytes"
        assert file_name == "report.pdf"
        client.get_attachment.assert_called_once_with("ref-uuid")

    def test_raises_http404_when_not_found(self):
        from django.http import Http404

        client = _make_couch_client(get_result=None)

        with pytest.raises(Http404):
            download_attachment("missing-id", couch_client=client)


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMedicalNoteSelectors:
    """Pure predicate selectors — no DB, MagicMock only."""

    def test_is_note_author_true_for_author(self):
        profile = MagicMock()
        note = MagicMock()
        note.author = profile
        assert is_note_author(profile, note) is True

    def test_is_note_author_false_for_non_author(self):
        note = MagicMock()
        note.author = MagicMock()
        assert is_note_author(MagicMock(), note) is False

    def test_is_attachment_author_true_when_note_author_matches(self):
        profile = MagicMock()
        attachment = MagicMock()
        attachment.medical_record.author = profile
        assert is_attachment_author(profile, attachment) is True

    def test_is_attachment_author_false_for_other_profile(self):
        attachment = MagicMock()
        attachment.medical_record.author = MagicMock()
        assert is_attachment_author(MagicMock(), attachment) is False

    def test_can_access_note_animal_delegates_to_animals_selector(self):
        profile = MagicMock()
        note = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.user_can_access_animal", return_value=True) as mock_selector:
            result = can_access_note_animal(profile, note)

        mock_selector.assert_called_once_with(profile, note.animal)
        assert result is True

    def test_can_access_note_animal_returns_false_when_denied(self):
        profile = MagicMock()
        note = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.user_can_access_animal", return_value=False):
            assert can_access_note_animal(profile, note) is False


# ---------------------------------------------------------------------------
# services/notes.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNextRouteForService:
    """next_route_for: pure routing logic — no DB, no mocks needed."""

    def test_biometric_event_routes_to_biometric_create(self):
        note = MagicMock()
        note.type_of_event = "biometric_record"
        note.id = "note-uuid"

        url_name, kwargs = next_route_for(note, "animal-uuid")

        assert url_name == "biometric_create"
        assert kwargs == {"pk": "animal-uuid", "note_id": "note-uuid"}

    def test_diet_note_routes_to_feeding_create(self):
        note = MagicMock()
        note.type_of_event = "diet_note"
        note.id = "note-uuid"

        url_name, kwargs = next_route_for(note, "animal-uuid")

        assert url_name == "feeding_create"
        assert kwargs == {"pk": "note-uuid"}

    def test_any_other_type_routes_to_full_timeline(self):
        note = MagicMock()
        note.type_of_event = "general"

        url_name, kwargs = next_route_for(note, "animal-uuid")

        assert url_name == "full_timeline_of_notes"
        assert kwargs == {"pk": "animal-uuid"}


@pytest.mark.unit
class TestCreateNoteService:
    """create_note: sets author/animal on unsaved instance, saves, calls save_m2m."""

    def test_assigns_fields_saves_and_returns_note(self):
        author = MagicMock()
        animal = MagicMock()
        form = MagicMock()
        note_mock = MagicMock()
        form.save.return_value = note_mock

        result = create_note(author, animal, form)

        form.save.assert_called_once_with(commit=False)
        assert note_mock.animal == animal
        assert note_mock.author == author
        note_mock.save.assert_called_once()
        form.save_m2m.assert_called_once()
        assert result is note_mock


@pytest.mark.unit
class TestUpdateNoteService:
    """update_note: conditionally reassigns animal, saves, sets additional_animals."""

    def test_reassigns_animal_when_present_in_cleaned_data(self):
        note = MagicMock()
        form = MagicMock()
        new_animal = MagicMock()
        form.cleaned_data = {"animal": new_animal, "additional_animals": []}

        update_note(note, form)

        assert note.animal == new_animal
        note.save.assert_called_once()

    def test_skips_animal_reassignment_when_not_in_cleaned_data(self):
        note = MagicMock()
        original_animal = note.animal
        form = MagicMock()
        form.cleaned_data = {"additional_animals": []}

        update_note(note, form)

        assert note.animal == original_animal

    def test_sets_additional_animals_m2m(self):
        note = MagicMock()
        form = MagicMock()
        extras = [MagicMock(), MagicMock()]
        form.cleaned_data = {"additional_animals": extras}

        update_note(note, form)

        note.additional_animals.set.assert_called_once_with(extras)


# ---------------------------------------------------------------------------
# services/notifications.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateEmailNotificationService:
    """create_email_notification: builds a 7-element bool days array before delegating.

    Uses SimpleNamespace so attribute assignment works without MagicMock interference.
    """

    def _notification_mock(self):
        return MagicMock()

    def test_selected_days_become_true_rest_false(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, ["0", "2", "6"])

        assert form_instance.days_of_week == [True, False, True, False, False, False, True]

    def test_empty_selection_produces_all_false(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, [])

        assert form_instance.days_of_week == [False] * 7

    def test_all_days_selected(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, ["0", "1", "2", "3", "4", "5", "6"])

        assert form_instance.days_of_week == [True] * 7

    def test_related_note_is_set_on_instance(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, [])

        assert form_instance.related_note is related_note


# ---------------------------------------------------------------------------
# services/biometrics.py — integration (requires DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def medical_note(db, user_profile):
    from ahc.apps.animals.models import Animal
    from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

    _, profile = user_profile
    animal = Animal.objects.create(full_name="Tester", owner=profile)
    return MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description="biometric base note",
        type_of_event="biometric_record",
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateBiometricRecordService:
    """create_biometric_record: branches across weight / height / custom sub-records."""

    def test_creates_weight_record(self, medical_note):
        from ahc.apps.medical_notes.services.biometrics import create_biometric_record

        record = create_biometric_record(
            medical_note.animal,
            medical_note,
            "weight",
            {"weight": 4.5, "weight_unit_to_present": "kg"},
        )

        assert record.animal == medical_note.animal
        assert record.weight_biometric_record is not None
        assert record.weight_biometric_record.weight == 4.5
        assert record.height_biometric_record is None
        assert record.custom_biometric_record is None

    def test_creates_height_record(self, medical_note):
        from ahc.apps.medical_notes.services.biometrics import create_biometric_record

        record = create_biometric_record(
            medical_note.animal,
            medical_note,
            "height",
            {"height": 30.0, "height_unit_to_present": "cm"},
        )

        assert record.height_biometric_record is not None
        assert record.height_biometric_record.height == 30.0
        assert record.weight_biometric_record is None

    def test_creates_custom_record(self, medical_note):
        from ahc.apps.medical_notes.services.biometrics import create_biometric_record

        record = create_biometric_record(
            medical_note.animal,
            medical_note,
            "custom",
            {"custom_name": "Temperature", "custom_value": "38.5", "custom_unit": "°C"},
        )

        assert record.custom_biometric_record is not None
        assert record.custom_biometric_record.record_name == "Temperature"
        assert record.weight_biometric_record is None
        assert record.height_biometric_record is None


@pytest.mark.unit
class TestCreateVaccinationNoteService:
    """create_vaccination_note: creates a MedicalRecord shell and a linked VaccinationNote."""

    def test_creates_shell_with_correct_type(self):
        from ahc.apps.medical_notes.services.vaccinations import create_vaccination_note

        author = MagicMock()
        animal = MagicMock()
        form = MagicMock()
        form.cleaned_data = {"vaccine_name": "Rabies"}

        vacc_instance = MagicMock()
        form.save.return_value = vacc_instance

        with patch("ahc.apps.medical_notes.services.vaccinations.MedicalRecord") as MockRecord:
            shell_instance = MagicMock()
            MockRecord.objects.create.return_value = shell_instance

            result = create_vaccination_note(author, animal, form)

        MockRecord.objects.create.assert_called_once_with(
            animal=animal,
            author=author,
            type_of_event="vaccination_note",
            short_description="Rabies",
        )
        assert vacc_instance.related_note is shell_instance
        vacc_instance.save.assert_called_once()
        assert result is vacc_instance

    def test_update_resets_reminder_sent_when_date_changes(self):
        from datetime import date

        from ahc.apps.medical_notes.services.vaccinations import update_vaccination_note

        vaccination = MagicMock()
        vaccination.reminder_date = date(2026, 1, 1)
        vaccination.reminder_sent = True
        vaccination.related_note.short_description = "Rabies"

        form = MagicMock()
        form.save.return_value = MagicMock()
        form.cleaned_data = {
            "vaccine_name": "Rabies",
            "reminder_date": date(2026, 6, 1),
        }

        result = update_vaccination_note(vaccination, form)
        assert result.reminder_sent is False

    def test_update_preserves_reminder_sent_when_date_unchanged(self):
        from datetime import date

        from ahc.apps.medical_notes.services.vaccinations import update_vaccination_note

        vaccination = MagicMock()
        vaccination.reminder_date = date(2026, 6, 1)
        vaccination.reminder_sent = True
        vaccination.related_note.short_description = "Rabies"

        form = MagicMock()
        form.save.return_value = MagicMock()
        form.cleaned_data = {
            "vaccine_name": "Rabies",
            "reminder_date": date(2026, 6, 1),
        }

        result = update_vaccination_note(vaccination, form)
        assert result.reminder_sent is True

    def test_delete_removes_satellite_and_shell(self):
        from ahc.apps.medical_notes.services.vaccinations import delete_vaccination_note

        vaccination = MagicMock()
        shell = MagicMock()
        vaccination.related_note = shell

        delete_vaccination_note(vaccination)

        vaccination.delete.assert_called_once()
        shell.delete.assert_called_once()


@pytest.mark.unit
class TestVaccinationSelectors:
    """due_vaccination_reminders: pure filtering logic verified with MagicMock."""

    def test_other_history_for_excludes_vaccination_note(self):
        from unittest.mock import patch

        from ahc.apps.medical_notes.selectors import other_history_for

        animal = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.MedicalRecord") as MockRecord:
            qs = MagicMock()
            MockRecord.objects.filter.return_value = qs
            qs.exclude.return_value = qs
            qs.prefetch_related.return_value = qs
            qs.order_by.return_value = qs

            other_history_for(animal)

            exclude_call = qs.exclude.call_args
            excluded_types = exclude_call[1]["type_of_event__in"]
            assert "vaccination_note" in excluded_types

    def test_other_records_for_excludes_vaccination_note(self):
        from ahc.apps.medical_notes.selectors import other_records_for

        animal = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.MedicalRecord") as MockRecord:
            qs = MagicMock()
            MockRecord.objects.filter.return_value = qs
            qs.exclude.return_value = qs
            qs.prefetch_related.return_value = qs
            qs.order_by.return_value = qs

            other_records_for(animal)

            exclude_call = qs.exclude.call_args
            excluded_types = exclude_call[1]["type_of_event__in"]
            assert "vaccination_note" in excluded_types


@pytest.fixture
def vaccination_animal(db, user_profile):
    from ahc.apps.animals.models import Animal

    _, profile = user_profile
    return Animal.objects.create(full_name="VaccTest", owner=profile), profile


@pytest.mark.integration
@pytest.mark.django_db
class TestVaccinationNoteIntegration:
    """End-to-end create / update / delete through services with a real SQLite DB."""

    def test_create_builds_shell_and_satellite(self, vaccination_animal):
        from datetime import date

        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
        from ahc.apps.medical_notes.services.vaccinations import create_vaccination_note

        animal, profile = vaccination_animal
        form = MagicMock()
        form.cleaned_data = {"vaccine_name": "Distemper", "reminder_date": None}
        vacc_mock = VaccinationNote(
            vaccine_name="Distemper",
            last_vaccination_date=date(2025, 1, 10),
            valid_until=date(2026, 1, 10),
            suggested_clinic="Happy Paws",
            reminder_date=None,
        )
        form.save.return_value = vacc_mock

        vaccination = create_vaccination_note(profile, animal, form)

        assert vaccination.related_note is not None
        assert vaccination.related_note.type_of_event == "vaccination_note"
        assert vaccination.related_note.short_description == "Distemper"
        assert MedicalRecord.objects.filter(type_of_event="vaccination_note", animal=animal).count() == 1

    def test_due_vaccination_reminders_returns_overdue_records(self, vaccination_animal):
        from datetime import date

        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
        from ahc.apps.medical_notes.selectors import due_vaccination_reminders

        animal, profile = vaccination_animal
        shell = MedicalRecord.objects.create(
            animal=animal, author=profile, type_of_event="vaccination_note", short_description="Flu"
        )
        VaccinationNote.objects.create(
            related_note=shell,
            vaccine_name="Flu",
            reminder_date=date(2026, 1, 1),
            reminder_sent=False,
        )

        due = list(due_vaccination_reminders(date(2026, 6, 1)))
        assert len(due) == 1
        assert due[0].vaccine_name == "Flu"

    def test_due_vaccination_reminders_excludes_already_sent(self, vaccination_animal):
        from datetime import date

        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
        from ahc.apps.medical_notes.selectors import due_vaccination_reminders

        animal, profile = vaccination_animal
        shell = MedicalRecord.objects.create(
            animal=animal, author=profile, type_of_event="vaccination_note", short_description="Parvovirus"
        )
        VaccinationNote.objects.create(
            related_note=shell,
            vaccine_name="Parvovirus",
            reminder_date=date(2026, 1, 1),
            reminder_sent=True,
        )

        due = list(due_vaccination_reminders(_date(2026, 6, 1)))
        assert due == []


# ---------------------------------------------------------------------------
# utils.py — build_timeline_base_query
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildTimelineBaseQuery:
    """build_timeline_base_query: pure query-string assembly."""

    def test_both_params(self):
        result = build_timeline_base_query("diet_note", "rabies")
        assert result == "type_of_event=diet_note&tag_name=rabies"

    def test_only_type_of_event(self):
        assert build_timeline_base_query("diet_note", "") == "type_of_event=diet_note"

    def test_only_tag_name(self):
        assert build_timeline_base_query("", "rabies") == "tag_name=rabies"

    def test_both_empty(self):
        assert build_timeline_base_query("", "") == ""


# ---------------------------------------------------------------------------
# selectors — is_author_of_any_note
# ---------------------------------------------------------------------------


@pytest.fixture
def diet_note_shell(db, user_profile):
    """A MedicalRecord of type diet_note owned by user_profile."""
    from ahc.apps.animals.models import Animal
    from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

    _, profile = user_profile
    animal = Animal.objects.create(full_name="Diet Tester", owner=profile)
    return MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description="Diet shell",
        type_of_event="diet_note",
    )


@pytest.fixture
def existing_feeding_note(db, diet_note_shell):
    """A persisted FeedingNote linked to diet_note_shell."""
    from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote

    return FeedingNote.objects.create(
        related_note=diet_note_shell,
        real_start_date=_date(2026, 1, 1),
        category="dry",
        product_name="Original Food",
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestIsAuthorOfAnyNote:
    def test_true_when_profile_has_authored_a_note(self, diet_note_shell, user_profile):
        _, profile = user_profile
        assert is_author_of_any_note(profile) is True

    def test_false_for_profile_with_no_notes(self, db, second_user_profile):
        _, other_profile = second_user_profile
        assert is_author_of_any_note(other_profile) is False


# ---------------------------------------------------------------------------
# View regression tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestDietRecordCreateView:
    """DietRecordCreateView (feeding_create): POST creates FeedingNote and redirects."""

    def test_valid_post_creates_feeding_note(self, client, user_profile, diet_note_shell):
        from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote

        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_create", kwargs={"pk": diet_note_shell.id})
        data = {
            "real_start_date": "2026-01-01",
            "category": "dry",
            "product_name": "New Food",
            "real_end_date": "",
            "producer": "",
            "dose_annotations": "",
            "purchase_source": "",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert FeedingNote.objects.filter(related_note=diet_note_shell).count() == 1

    def test_redirects_to_diet_list(self, client, user_profile, diet_note_shell):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_create", kwargs={"pk": diet_note_shell.id})
        data = {
            "real_start_date": "2026-01-01",
            "category": "dry",
            "product_name": "New Food",
        }
        response = client.post(url, data)
        expected_redirect = reverse("note_related_diets", kwargs={"pk": str(diet_note_shell.id)})
        assert response["Location"] == expected_redirect

    def test_unauthenticated_redirects_to_login(self, client, diet_note_shell):
        url = reverse("feeding_create", kwargs={"pk": diet_note_shell.id})
        response = client.post(url, {})
        assert response.status_code == 302
        assert "/login" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestEditDietRecordView:
    """EditDietRecordView (feeding_edit): POST updates FeedingNote and redirects to diet list.

    This test asserts the CORRECTED behaviour. Against the original code the view
    returned 404 because form_valid tried to fetch an EmailNotification using the
    FeedingNote pk — a type/identity mismatch.
    """

    def test_valid_post_updates_feeding_note(self, client, user_profile, existing_feeding_note):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_edit", kwargs={"pk": existing_feeding_note.pk})
        data = {
            "real_start_date": "2026-03-01",
            "category": "wet",
            "product_name": "Updated Food",
            "real_end_date": "",
            "producer": "",
            "dose_annotations": "",
            "purchase_source": "",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        existing_feeding_note.refresh_from_db()
        assert existing_feeding_note.product_name == "Updated Food"

    def test_redirects_to_diet_list_of_parent_note(self, client, user_profile, existing_feeding_note):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_edit", kwargs={"pk": existing_feeding_note.pk})
        data = {
            "real_start_date": "2026-03-01",
            "category": "wet",
            "product_name": "Updated Food",
        }
        response = client.post(url, data)
        expected_redirect = reverse(
            "note_related_diets",
            kwargs={"pk": str(existing_feeding_note.related_note.id)},
        )
        assert response["Location"] == expected_redirect


@pytest.mark.integration
@pytest.mark.django_db
class TestFeedingNoteListViewAccess:
    """FeedingNoteListView (note_related_diets): permission mixin enforced after refactor."""

    def test_owner_can_access(self, client, user_profile, diet_note_shell):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("note_related_diets", kwargs={"pk": diet_note_shell.id})
        response = client.get(url)
        assert response.status_code == 200

    def test_stranger_is_denied(self, client, second_user_profile, diet_note_shell):
        stranger, _ = second_user_profile
        client.force_login(stranger)
        url = reverse("note_related_diets", kwargs={"pk": diet_note_shell.id})
        response = client.get(url)
        assert response.status_code == 403
