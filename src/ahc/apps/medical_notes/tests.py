from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError

from ahc.apps.medical_notes.models.type_measurement_notes import (
    BiometricHeightRecords,
    BiometricWeightRecords,
)
from ahc.apps.medical_notes.selectors import (
    can_access_note_animal,
    is_attachment_author,
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
