from datetime import date

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote
from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord, BiometricWeightRecords
from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote


@pytest.fixture
def snapshot_animal(db, user_profile):
    """An animal owned by user_profile with one record of each snapshot-relevant kind."""
    _, profile = user_profile
    animal = Animal.objects.create(
        full_name="Snappy",
        owner=profile,
        species="dog",
        breed="mixed",
        sex="m",
        birthdate=date(2020, 5, 1),
        dietary_restrictions="no grain",
        first_contact_vet="Dr. Vet",
        first_contact_medical_place="Happy Paws Clinic",
    )
    visit = MedicalRecord.objects.create(
        animal=animal, author=profile, short_description="Yearly check", type_of_event="medical_visit"
    )
    MedicalRecordAttachment.objects.create(
        medical_record=visit, file_name="xray.pdf", couch_id="couch-xray-1", description="X-ray scan"
    )
    diet = MedicalRecord.objects.create(
        animal=animal, author=profile, short_description="New kibble", type_of_event="diet_note"
    )
    FeedingNote.objects.create(
        related_note=diet,
        real_start_date=date(2026, 1, 1),
        category="dry",
        product_name="Kibble",
        producer="Acme",
        dose_annotations="100g daily",
    )
    MedicalRecord.objects.create(animal=animal, author=profile, short_description="Quick note", type_of_event="fast_note")
    shell = MedicalRecord.objects.create(
        animal=animal, author=profile, short_description="Weighing", type_of_event="biometric_record"
    )
    weight = BiometricWeightRecords.objects.create(weight=5)
    BiometricRecord.objects.create(animal=animal, related_note=shell, weight_biometric_record=weight)
    vacc_shell = MedicalRecord.objects.create(
        animal=animal, author=profile, short_description="Rabies shot", type_of_event="vaccination_note"
    )
    VaccinationNote.objects.create(
        related_note=vacc_shell,
        vaccine_name="Rabies",
        last_vaccination_date=date(2026, 3, 1),
        valid_until=date(2027, 3, 1),
        suggested_clinic="Happy Paws Clinic",
        reminder_date=date(2027, 2, 1),
        reminder_sent=True,
    )
    return animal, profile


@pytest.fixture
def snapshot_dir(tmp_path, settings):
    """Point the private snapshot storage at a per-test directory."""
    settings.OFFLINE_SNAPSHOT_ROOT = tmp_path
    return tmp_path
