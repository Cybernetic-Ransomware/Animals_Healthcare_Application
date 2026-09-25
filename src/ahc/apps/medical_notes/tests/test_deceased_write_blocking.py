from datetime import date as _date

import pytest
from django.urls import reverse


@pytest.mark.integration
@pytest.mark.django_db
class TestDeceasedAnimalWriteBlocking:
    """Verify all medical-notes write paths block deceased animals."""

    @pytest.fixture
    def setup(self, db, user_profile, second_user_profile):
        from ahc.apps.animals.models import Animal, AnimalShare
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

        _, owner_profile = user_profile
        owner_user, _ = user_profile
        _, carer_profile = second_user_profile
        carer_user, _ = second_user_profile

        living = Animal.objects.create(full_name="Living", owner=owner_profile)
        deceased = Animal.objects.create(full_name="Passed", owner=owner_profile, date_of_death=_date(2024, 1, 1))
        AnimalShare.objects.create(animal=deceased, carer=carer_profile)
        AnimalShare.objects.create(animal=living, carer=carer_profile)

        note_on_living = MedicalRecord.objects.create(
            animal=living, author=owner_profile, short_description="live note", type_of_event="fast_note"
        )
        return {
            "owner_user": owner_user,
            "carer_user": carer_user,
            "owner_profile": owner_profile,
            "carer_profile": carer_profile,
            "living": living,
            "deceased": deceased,
            "note_on_living": note_on_living,
        }

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_owner_cannot_create_note_on_deceased(self, setup):
        s = setup
        # medical_notes URLs are mounted under /note/ (see ahc/urls.py)
        response = self._client_for(s["owner_user"]).post(
            f"/note/{s['deceased'].id}/create/",
            {"type_of_event": "fast_note", "short_description": "new note"},
        )
        assert response.status_code == 403

    def test_carer_cannot_create_note_on_deceased(self, setup):
        s = setup
        response = self._client_for(s["carer_user"]).post(
            f"/note/{s['deceased'].id}/create/",
            {"type_of_event": "fast_note", "short_description": "carer note"},
        )
        assert response.status_code == 403

    def test_deceased_animal_not_in_batch_allowed_set(self, setup):
        """Deceased animal must never appear in the formset offered by BiometricBatchCreateView."""
        s = setup
        response = self._client_for(s["owner_user"]).get(reverse("biometric_batch"))
        assert response.status_code == 200
        # BiometricBatchCreateView._build_context stores animals inside 'rows' as (form, animal) tuples
        offered_ids = {str(animal.id) for _, animal in response.context["rows"]}
        assert str(s["deceased"].id) not in offered_ids
        assert str(s["living"].id) in offered_ids

    def test_form_queryset_rejects_deceased_uuid_in_additional_animals(self, setup):
        """MedicalRecordForm.additional_animals queryset must reject a deceased animal UUID."""
        from ahc.apps.medical_notes.forms.type_basic_note import MedicalRecordForm

        s = setup
        form = MedicalRecordForm(
            data={
                "type_of_event": "fast_note",
                "short_description": "test",
                "additional_animals": [str(s["deceased"].id)],
            },
            profile=s["owner_profile"],
            exclude_id=s["living"].id,
        )
        assert not form.is_valid()
        assert "additional_animals" in form.errors

    def test_can_access_note_animal_returns_false_for_deceased(self, setup):
        """can_access_note_animal must block even the owner on a deceased animal's note."""
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.selectors import can_access_note_animal

        s = setup
        deceased_note = MedicalRecord.objects.create(
            animal=s["deceased"], author=s["owner_profile"], short_description="old note", type_of_event="fast_note"
        )
        assert can_access_note_animal(s["owner_profile"], deceased_note) is False
        assert can_access_note_animal(s["carer_profile"], deceased_note) is False

    def test_due_vaccination_reminders_excludes_deceased(self, setup):
        """Vaccination reminders must not fire for deceased animals."""
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
        from ahc.apps.medical_notes.selectors import due_vaccination_reminders

        s = setup
        living_note = MedicalRecord.objects.create(
            animal=s["living"], author=s["owner_profile"], short_description="vacc base", type_of_event="vaccination_note"
        )
        deceased_note = MedicalRecord.objects.create(
            animal=s["deceased"],
            author=s["owner_profile"],
            short_description="deceased vacc",
            type_of_event="vaccination_note",
        )
        today = _date(2025, 1, 1)
        living_vacc = VaccinationNote.objects.create(related_note=living_note, reminder_date=today, reminder_sent=False)
        deceased_vacc = VaccinationNote.objects.create(related_note=deceased_note, reminder_date=today, reminder_sent=False)
        reminders = list(due_vaccination_reminders(today))
        reminder_ids = {v.pk for v in reminders}
        assert living_vacc.pk in reminder_ids
        assert deceased_vacc.pk not in reminder_ids
