"""Tests for the offline_snapshots exporter and management command.

Snapshot files are read back with the stdlib sqlite3 module on purpose:
this proves the artifact produced via the Turso driver is a standard,
portable SQLite database.
"""

import sqlite3
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote
from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord, BiometricWeightRecords
from ahc.apps.offline_snapshots.services.exporter import export_animal_snapshot
from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION


def _query(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


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
    return animal, profile


@pytest.mark.integration
class TestOwnerSnapshotExport:
    def test_creates_file_with_valid_manifest(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal

        path = export_animal_snapshot(animal, profile, tmp_path)

        assert path.exists()
        assert path.name == f"animal_{animal.id}.db"
        (manifest,) = _query(path, "SELECT * FROM snapshot_manifest")
        assert manifest["animal_id"] == str(animal.id)
        assert manifest["schema_version"] == SCHEMA_VERSION
        assert manifest["generated_at"]
        assert manifest["generated_by"] == profile.user.username
        assert manifest["is_read_only"] == 1

    def test_animal_row_has_all_fields_for_owner(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal

        path = export_animal_snapshot(animal, profile, tmp_path)

        (row,) = _query(path, "SELECT * FROM animal_snapshot")
        assert row["id"] == str(animal.id)
        assert row["full_name"] == "Snappy"
        assert row["species"] == "dog"
        assert row["breed"] == "mixed"
        assert row["sex"] == "m"
        assert row["birthdate"] == "2020-05-01"
        assert row["dietary_restrictions"] == "no grain"
        assert row["first_contact_vet"] == "Dr. Vet"
        assert row["first_contact_medical_place"] == "Happy Paws Clinic"

    def test_contains_only_this_animals_records(self, snapshot_animal, second_user_profile, tmp_path):
        animal, profile = snapshot_animal
        _, other_profile = second_user_profile
        other_animal = Animal.objects.create(full_name="Stranger", owner=other_profile)
        foreign = MedicalRecord.objects.create(
            animal=other_animal, author=other_profile, short_description="Foreign", type_of_event="medical_visit"
        )

        path = export_animal_snapshot(animal, profile, tmp_path)

        rows = _query(path, "SELECT id, animal_id FROM medical_record_snapshot")
        assert len(rows) == 4
        assert {row["animal_id"] for row in rows} == {str(animal.id)}
        assert str(foreign.id) not in {row["id"] for row in rows}

    def test_biometric_rows_are_flattened_with_units(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal

        path = export_animal_snapshot(animal, profile, tmp_path)

        (row,) = _query(path, "SELECT * FROM biometric_snapshot")
        assert row["animal_id"] == str(animal.id)
        assert Decimal(row["weight"]) == Decimal(5)
        assert row["weight_unit"] == "g"
        assert row["height"] is None
        assert row["custom_name"] is None

    def test_attachment_table_holds_metadata_only(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal

        path = export_animal_snapshot(animal, profile, tmp_path)

        (row,) = _query(path, "SELECT * FROM attachment_metadata_snapshot")
        assert row["file_name"] == "xray.pdf"
        assert row["couch_id"] == "couch-xray-1"
        columns = {info["name"] for info in _query(path, "PRAGMA table_info(attachment_metadata_snapshot)")}
        assert columns == {"id", "medical_record_id", "file_name", "description", "couch_id", "upload_date"}


@pytest.mark.integration
class TestSnapshotRebuild:
    def test_existing_file_without_force_raises(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        export_animal_snapshot(animal, profile, tmp_path)

        with pytest.raises(FileExistsError):
            export_animal_snapshot(animal, profile, tmp_path)

    def test_force_rebuilds_and_replaces_file(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        first_path = export_animal_snapshot(animal, profile, tmp_path)
        (first_manifest,) = _query(first_path, "SELECT generated_at FROM snapshot_manifest")

        second_path = export_animal_snapshot(animal, profile, tmp_path, force=True)

        assert second_path == first_path
        assert not (tmp_path / f"animal_{animal.id}.tmp.db").exists()
        (second_manifest,) = _query(second_path, "SELECT generated_at FROM snapshot_manifest")
        assert second_manifest["generated_at"] >= first_manifest["generated_at"]


@pytest.mark.integration
class TestShareFiltering:
    def test_diet_only_carer_gets_filtered_snapshot(self, snapshot_animal, second_user_profile, tmp_path):
        animal, _ = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)

        path = export_animal_snapshot(animal, carer, tmp_path)

        (row,) = _query(path, "SELECT * FROM animal_snapshot")
        assert row["full_name"] == "Snappy"
        assert row["species"] is None
        assert row["first_contact_vet"] is None
        assert row["dietary_restrictions"] == "no grain"
        records = _query(path, "SELECT type_of_event FROM medical_record_snapshot")
        assert {r["type_of_event"] for r in records} == {"diet_note"}
        assert len(_query(path, "SELECT * FROM feeding_note_snapshot")) == 1
        assert _query(path, "SELECT * FROM biometric_snapshot") == []
        assert _query(path, "SELECT * FROM attachment_metadata_snapshot") == []

    def test_profile_without_access_is_denied(self, snapshot_animal, second_user_profile, tmp_path):
        animal, _ = snapshot_animal
        _, stranger = second_user_profile

        with pytest.raises(PermissionDenied):
            export_animal_snapshot(animal, stranger, tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_expired_share_is_denied(self, snapshot_animal, second_user_profile, tmp_path):
        animal, _ = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(
            animal=animal, carer=carer, allow_diet=True, valid_until=date.today() - timedelta(days=1)
        )

        with pytest.raises(PermissionDenied):
            export_animal_snapshot(animal, carer, tmp_path)


@pytest.mark.integration
class TestExportCommand:
    def test_exports_as_owner_by_default(self, snapshot_animal, tmp_path):
        animal, _ = snapshot_animal

        call_command("export_animal_snapshot", str(animal.id), "--output-dir", str(tmp_path))

        assert (tmp_path / f"animal_{animal.id}.db").exists()

    def test_unknown_animal_raises_command_error(self, db, tmp_path):
        with pytest.raises(CommandError, match="No animal found"):
            call_command("export_animal_snapshot", "not-a-uuid", "--output-dir", str(tmp_path))

    def test_unknown_username_raises_command_error(self, snapshot_animal, tmp_path):
        animal, _ = snapshot_animal

        with pytest.raises(CommandError, match="No profile found"):
            call_command("export_animal_snapshot", str(animal.id), "--username", "ghost", "--output-dir", str(tmp_path))

    def test_denied_profile_raises_command_error(self, snapshot_animal, second_user_profile, tmp_path):
        animal, _ = snapshot_animal
        user, _ = second_user_profile

        with pytest.raises(CommandError, match="no access"):
            call_command(
                "export_animal_snapshot", str(animal.id), "--username", user.username, "--output-dir", str(tmp_path)
            )
