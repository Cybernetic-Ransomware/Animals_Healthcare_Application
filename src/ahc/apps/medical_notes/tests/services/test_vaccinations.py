from datetime import date as _date
from unittest.mock import MagicMock, patch

import pytest


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
