import uuid
from decimal import Decimal

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord
from ahc.apps.medical_notes.services.biometrics import create_batch_biometric_records, create_biometric_record


@pytest.fixture
def medical_note(db, user_profile):
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


@pytest.fixture
def batch_animals(db, user_profile):
    """Three animals owned by user_profile for batch service tests."""
    _, profile = user_profile
    a1 = Animal.objects.create(full_name="Alpha", owner=profile)
    a2 = Animal.objects.create(full_name="Beta", owner=profile)
    a3 = Animal.objects.create(full_name="Gamma", owner=profile)
    return (a1, a2, a3), profile


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateBatchBiometricRecordsService:
    """create_batch_biometric_records: creates N pairs, enforces allowed_ids, no signal orphans."""

    def test_creates_expected_number_of_pairs(self, batch_animals):
        (a1, a2, _), profile = batch_animals
        rows = [
            (a1, {"weight": Decimal("4.5"), "weight_unit_to_present": "kg"}),
            (a2, {"weight": Decimal("8.0"), "weight_unit_to_present": "kg"}),
        ]
        n = create_batch_biometric_records(profile, "weight", rows, allowed_ids={a1.id, a2.id})

        assert n == 2
        assert MedicalRecord.objects.filter(type_of_event="biometric_record", author=profile).count() == 2
        assert BiometricRecord.objects.filter(animal__in=[a1, a2]).count() == 2

    def test_skips_animal_not_in_allowed_ids(self, batch_animals):
        (a1, _, _), profile = batch_animals
        outsider_id = uuid.uuid4()
        rows = [
            (a1, {"weight": Decimal("5.0"), "weight_unit_to_present": "kg"}),
        ]
        n = create_batch_biometric_records(profile, "weight", rows, allowed_ids={outsider_id})

        assert n == 0
        assert BiometricRecord.objects.count() == 0

    def test_no_orphaned_notes_after_batch(self, batch_animals):
        """Regression: the clean_orphaned_metric_records signal must not delete sibling notes.

        This test fails if the service creates all MedicalRecord rows before any
        BiometricRecord — the first BiometricRecord save would then wipe the still-empty
        sibling notes. Correct sequential (note, biometry) pairing prevents this.
        """
        (a1, a2, a3), profile = batch_animals
        rows = [
            (a1, {"weight": Decimal("3.0"), "weight_unit_to_present": "g"}),
            (a2, {"weight": Decimal("6.0"), "weight_unit_to_present": "g"}),
            (a3, {"weight": Decimal("9.0"), "weight_unit_to_present": "g"}),
        ]
        create_batch_biometric_records(profile, "weight", rows, allowed_ids={a1.id, a2.id, a3.id})

        note_count = MedicalRecord.objects.filter(type_of_event="biometric_record", author=profile).count()
        biometric_count = BiometricRecord.objects.filter(animal__in=[a1, a2, a3]).count()
        assert note_count == 3, f"Expected 3 notes, got {note_count} (signal deleted orphans)"
        assert biometric_count == 3
