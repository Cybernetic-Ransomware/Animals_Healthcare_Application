"""Tests for the offline_snapshots exporter and management command.

Snapshot files are read back with the stdlib sqlite3 module on purpose:
this proves the artifact produced via the Turso driver is a standard,
portable SQLite database.
"""

import json
import logging
import sqlite3
import uuid
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from ahc.apps.animals.models import Animal, AnimalShare, ShareCategory
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote
from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord, BiometricWeightRecords
from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
from ahc.apps.offline_snapshots import tasks as snapshot_tasks
from ahc.apps.offline_snapshots.models import AnimalSnapshot, DownloadOutcome, SnapshotDownloadLog, SnapshotStatus
from ahc.apps.offline_snapshots.services import lifecycle
from ahc.apps.offline_snapshots.services.exporter import export_animal_snapshot
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    request_snapshot_build,
    run_snapshot_build,
)
from ahc.apps.offline_snapshots.services.pruning import prune_snapshots
from ahc.apps.offline_snapshots.services.schema import EXPORTER_VERSION, SCHEMA_VERSION, TABLES
from ahc.apps.offline_snapshots.services.storage import snapshot_path
from celery_notifications.config import celery_obj


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
        assert len(manifest["source_revision"]) == 64
        assert all(char in "0123456789abcdef" for char in manifest["source_revision"])

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
        assert len(rows) == 5
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

    def test_vaccination_rows_hold_domain_fields_without_reminder_state(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal

        path = export_animal_snapshot(animal, profile, tmp_path)

        (row,) = _query(path, "SELECT * FROM vaccination_note_snapshot")
        assert row["vaccine_name"] == "Rabies"
        assert row["last_vaccination_date"] == "2026-03-01"
        assert row["valid_until"] == "2027-03-01"
        assert row["suggested_clinic"] == "Happy Paws Clinic"
        columns = {info["name"] for info in _query(path, "PRAGMA table_info(vaccination_note_snapshot)")}
        expected = {"id", "medical_record_id", "vaccine_name", "last_vaccination_date", "valid_until", "suggested_clinic"}
        assert columns == expected

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
        assert not list(tmp_path.glob("*.tmp.db"))
        (second_manifest,) = _query(second_path, "SELECT generated_at FROM snapshot_manifest")
        assert second_manifest["generated_at"] >= first_manifest["generated_at"]


@pytest.mark.integration
class TestSourceRevision:
    @staticmethod
    def _revision(path):
        (manifest,) = _query(path, "SELECT source_revision FROM snapshot_manifest")
        return manifest["source_revision"]

    def test_identical_data_yields_identical_revision(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        first = self._revision(export_animal_snapshot(animal, profile, tmp_path))

        second = self._revision(export_animal_snapshot(animal, profile, tmp_path, force=True))

        assert first == second

    def test_animal_field_change_changes_revision(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        first = self._revision(export_animal_snapshot(animal, profile, tmp_path))

        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        second = self._revision(export_animal_snapshot(animal, profile, tmp_path, force=True))

        assert first != second

    def test_feeding_note_change_changes_revision(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        first = self._revision(export_animal_snapshot(animal, profile, tmp_path))

        note = FeedingNote.objects.get(related_note__animal=animal)
        note.dose_annotations = "200g daily"
        note.save()
        second = self._revision(export_animal_snapshot(animal, profile, tmp_path, force=True))

        assert first != second


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
        assert _query(path, "SELECT * FROM vaccination_note_snapshot") == []
        assert _query(path, "SELECT * FROM attachment_metadata_snapshot") == []

    def test_vaccination_only_carer_gets_filtered_snapshot(self, snapshot_animal, second_user_profile, tmp_path):
        animal, _ = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_vaccinations=True)

        path = export_animal_snapshot(animal, carer, tmp_path)

        records = _query(path, "SELECT type_of_event FROM medical_record_snapshot")
        assert {r["type_of_event"] for r in records} == {"vaccination_note"}
        (vaccination,) = _query(path, "SELECT * FROM vaccination_note_snapshot")
        assert vaccination["vaccine_name"] == "Rabies"
        assert vaccination["valid_until"] == "2027-03-01"
        (row,) = _query(path, "SELECT species, dietary_restrictions, first_contact_vet FROM animal_snapshot")
        assert row["species"] is None
        assert row["dietary_restrictions"] is None
        assert row["first_contact_vet"] is None
        assert _query(path, "SELECT * FROM feeding_note_snapshot") == []
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


@pytest.fixture
def snapshot_dir(tmp_path, settings):
    """Point the private snapshot storage at a per-test directory."""
    settings.OFFLINE_SNAPSHOT_ROOT = tmp_path
    return tmp_path


def _saved_response_db(response, tmp_path):
    """Write a streamed download response to disk so it can be queried with sqlite3."""
    target = tmp_path / "downloaded.db"
    target.write_bytes(b"".join(response.streaming_content))
    return target


@pytest.mark.unit
class TestSnapshotStorage:
    def test_traversal_key_is_rejected(self):
        with pytest.raises(ValueError, match="Invalid snapshot storage key"):
            snapshot_path("../../etc/passwd")

    def test_snapshot_root_is_not_under_media_root(self):
        snapshot_root = Path(django_settings.OFFLINE_SNAPSHOT_ROOT).resolve()
        media_root = Path(django_settings.MEDIA_ROOT).resolve()
        assert not snapshot_root.is_relative_to(media_root)


@pytest.mark.integration
class TestSnapshotLifecycle:
    def test_owner_build_creates_ready_current_snapshot(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal

        snapshot = get_or_create_snapshot(animal, profile)

        assert snapshot.status == SnapshotStatus.READY
        assert snapshot.is_current is True
        assert snapshot.schema_version == SCHEMA_VERSION
        assert len(snapshot.source_revision) == 64
        assert snapshot.file_size_bytes > 0
        assert snapshot.allowed_categories_json == sorted(c.value for c in ShareCategory)
        assert (snapshot_dir / f"{snapshot.id}.db").exists()

    def test_diet_carer_gets_own_filtered_snapshot(self, snapshot_animal, second_user_profile, snapshot_dir, tmp_path):
        animal, owner = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)

        owner_snapshot = get_or_create_snapshot(animal, owner)
        carer_snapshot = get_or_create_snapshot(animal, carer)

        assert carer_snapshot.id != owner_snapshot.id
        assert carer_snapshot.storage_key != owner_snapshot.storage_key
        assert carer_snapshot.allowed_categories_json == [ShareCategory.DIET.value]
        records = _query(snapshot_path(carer_snapshot.storage_key), "SELECT type_of_event FROM medical_record_snapshot")
        assert {r["type_of_event"] for r in records} == {"diet_note"}

    def test_stranger_is_denied_and_nothing_created(self, snapshot_animal, second_user_profile, snapshot_dir):
        animal, _ = snapshot_animal
        _, stranger = second_user_profile

        with pytest.raises(PermissionDenied):
            get_or_create_snapshot(animal, stranger)
        assert AnimalSnapshot.objects.count() == 0
        assert list(snapshot_dir.iterdir()) == []

    def test_unchanged_data_returns_same_artifact(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        first = get_or_create_snapshot(animal, profile)

        second = get_or_create_snapshot(animal, profile)

        assert second.id == first.id
        assert second.generated_at == first.generated_at
        assert AnimalSnapshot.objects.count() == 1

    def test_changed_data_creates_new_current_artifact(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        first = get_or_create_snapshot(animal, profile)

        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        second = get_or_create_snapshot(animal, profile)

        assert second.id != first.id
        assert second.source_revision != first.source_revision
        assert second.is_current is True
        first.refresh_from_db()
        assert first.is_current is False
        assert first.superseded_at is not None
        assert snapshot_path(first.storage_key).exists()

    def test_force_creates_new_artifact_for_identical_data(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        first = get_or_create_snapshot(animal, profile)

        second = get_or_create_snapshot(animal, profile, force=True)

        assert second.id != first.id
        assert second.source_revision == first.source_revision
        assert second.is_current is True

    def test_failed_build_keeps_previous_artifact(self, snapshot_animal, snapshot_dir, monkeypatch):
        animal, profile = snapshot_animal
        first = get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        failed = get_or_create_snapshot(animal, profile)

        assert failed.status == SnapshotStatus.FAILED
        assert failed.error_message == "boom"
        assert failed.is_current is False
        first.refresh_from_db()
        assert first.is_current is True
        assert snapshot_path(first.storage_key).exists()


@pytest.mark.integration
class TestSnapshotEndpoints:
    @staticmethod
    def _manifest_url(animal):
        return f"/pet/{animal.id}/offline-snapshot/"

    @staticmethod
    def _rebuild_url(animal):
        return f"/pet/{animal.id}/offline-snapshot/rebuild/"

    @staticmethod
    def _download_url(animal, snapshot_id):
        return f"/pet/{animal.id}/offline-snapshot/{snapshot_id}/download/"

    def test_manifest_missing_reports_can_generate(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.get(self._manifest_url(animal))

        assert response.status_code == 200
        assert response.json() == {"animal_id": str(animal.id), "status": "missing", "can_generate": True}

    def test_rebuild_then_manifest_round_trip(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        rebuild_response = client.post(self._rebuild_url(animal))
        rebuild = rebuild_response.json()
        run_snapshot_build(rebuild["snapshot_id"])
        manifest = client.get(self._manifest_url(animal)).json()

        assert rebuild_response.status_code == 202
        assert rebuild["status"] == "building"
        assert rebuild["download_url"] is None
        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == rebuild["snapshot_id"]
        assert manifest["source_revision"] == rebuild["source_revision"]
        assert manifest["schema_version"] == SCHEMA_VERSION
        assert manifest["file_size_bytes"] > 0
        assert manifest["building_snapshot_id"] is None
        assert manifest["download_url"] == self._download_url(animal, rebuild["snapshot_id"])

    def test_stranger_gets_403_on_all_endpoints(self, snapshot_animal, second_user_profile, snapshot_dir, client):
        animal, owner = snapshot_animal
        snapshot = get_or_create_snapshot(animal, owner)
        stranger_user, _ = second_user_profile
        client.force_login(stranger_user)

        assert client.get(self._manifest_url(animal)).status_code == 403
        assert client.post(self._rebuild_url(animal)).status_code == 403
        assert client.get(self._download_url(animal, snapshot.id)).status_code == 403

    def test_carer_downloads_own_filtered_file(self, snapshot_animal, second_user_profile, snapshot_dir, client, tmp_path):
        animal, _ = snapshot_animal
        carer_user, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        snapshot = get_or_create_snapshot(animal, carer)
        client.force_login(carer_user)

        response = client.get(self._download_url(animal, snapshot.id))

        assert response.status_code == 200
        downloaded = _saved_response_db(response, tmp_path)
        (manifest,) = _query(downloaded, "SELECT source_revision FROM snapshot_manifest")
        assert manifest["source_revision"] == snapshot.source_revision
        records = _query(downloaded, "SELECT type_of_event FROM medical_record_snapshot")
        assert {r["type_of_event"] for r in records} == {"diet_note"}

    def test_carer_cannot_download_owners_snapshot(self, snapshot_animal, second_user_profile, snapshot_dir, client):
        animal, owner = snapshot_animal
        owner_snapshot = get_or_create_snapshot(animal, owner)
        carer_user, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        client.force_login(carer_user)

        response = client.get(self._download_url(animal, owner_snapshot.id))

        assert response.status_code == 404

    def test_download_headers(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        response = client.get(self._download_url(animal, snapshot.id))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.sqlite3"
        assert "attachment" in response["Content-Disposition"]
        assert f"animal_{animal.id}_snapshot.db" in response["Content-Disposition"]

    def test_manifest_reflects_new_revision_after_change(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)
        first = client.post(self._rebuild_url(animal)).json()
        run_snapshot_build(first["snapshot_id"])

        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        second = client.post(self._rebuild_url(animal)).json()
        run_snapshot_build(second["building_snapshot_id"])
        manifest = client.get(self._manifest_url(animal)).json()

        # The rebuild response keeps the stale READY current as its subject;
        # the enqueued replacement is addressed via building_snapshot_id.
        assert second["snapshot_id"] == first["snapshot_id"]
        assert second["is_stale"] is True
        assert second["latest_source_revision"] != first["source_revision"]
        assert manifest["source_revision"] == second["latest_source_revision"]
        assert manifest["is_stale"] is False
        assert manifest["download_url"] == self._download_url(animal, second["building_snapshot_id"])

    def test_manifest_reports_missing_when_file_deleted(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        snapshot_path(snapshot.storage_key).unlink()
        client.force_login(profile.user)

        response = client.get(self._manifest_url(animal))

        assert response.status_code == 200
        assert response.json() == {"animal_id": str(animal.id), "status": "missing", "can_generate": True}

    def test_anonymous_is_redirected_to_login(self, snapshot_animal, snapshot_dir, client):
        animal, _ = snapshot_animal

        response = client.get(self._manifest_url(animal))

        assert response.status_code == 302
        assert "login" in response["Location"]


@pytest.mark.integration
class TestPruneCommand:
    def test_prune_keeps_current_and_recent_superseded(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        artifacts = [get_or_create_snapshot(animal, profile, force=True) for _ in range(4)]
        oldest = artifacts[0]

        call_command("prune_animal_snapshots", "--keep", "3")

        remaining = set(AnimalSnapshot.objects.values_list("id", flat=True))
        assert remaining == {a.id for a in artifacts[1:]}
        assert not snapshot_path(oldest.storage_key).exists()
        assert all(snapshot_path(a.storage_key).exists() for a in artifacts[1:])

    def test_prune_deletes_old_failed_rows(self, snapshot_animal, snapshot_dir, monkeypatch):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        failed = get_or_create_snapshot(animal, profile, force=True)
        AnimalSnapshot.objects.filter(id=failed.id).update(generated_at=timezone.now() - timedelta(days=8))

        call_command("prune_animal_snapshots", "--failed-days", "7")

        remaining = set(AnimalSnapshot.objects.values_list("id", flat=True))
        assert remaining == {current.id}


def _manifest_url(animal):
    return f"/pet/{animal.id}/offline-snapshot/"


def _rebuild_url(animal):
    return f"/pet/{animal.id}/offline-snapshot/rebuild/"


def _widget_url(animal):
    return f"/pet/{animal.id}/offline-snapshot/widget/"


def _download_url(animal, snapshot_id):
    return f"/pet/{animal.id}/offline-snapshot/{snapshot_id}/download/"


@pytest.fixture
def captured_enqueues(monkeypatch):
    """Record build_snapshot_task.apply_async calls instead of talking to the broker."""
    calls = []
    monkeypatch.setattr(snapshot_tasks.build_snapshot_task, "apply_async", lambda **kwargs: calls.append(kwargs))
    return calls


@pytest.mark.integration
class TestAsyncRebuildRequest:
    def test_post_without_current_returns_202_and_enqueues(
        self, snapshot_animal, snapshot_dir, client, captured_enqueues, django_capture_on_commit_callbacks
    ):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(_rebuild_url(animal))

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "building"
        assert body["download_url"] is None
        snapshot = AnimalSnapshot.objects.get(id=body["snapshot_id"])
        assert snapshot.status == SnapshotStatus.BUILDING
        assert snapshot.task_id
        assert captured_enqueues == [{"args": [str(snapshot.id)], "task_id": snapshot.task_id}]

    def test_fresh_current_returns_200_without_enqueue(
        self, snapshot_animal, snapshot_dir, client, captured_enqueues, django_capture_on_commit_callbacks
    ):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(_rebuild_url(animal))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["snapshot_id"] == str(current.id)
        assert body["download_url"] == _download_url(animal, current.id)
        assert captured_enqueues == []

    def test_second_post_during_building_is_deduped(
        self, snapshot_animal, snapshot_dir, client, captured_enqueues, django_capture_on_commit_callbacks
    ):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        with django_capture_on_commit_callbacks(execute=True):
            first = client.post(_rebuild_url(animal))
        with django_capture_on_commit_callbacks(execute=True):
            second = client.post(_rebuild_url(animal), {"force": "1"})

        assert first.status_code == 202
        assert second.status_code == 202
        assert second.json()["snapshot_id"] == first.json()["snapshot_id"]
        assert AnimalSnapshot.objects.filter(status=SnapshotStatus.BUILDING).count() == 1
        assert len(captured_enqueues) == 1

    def test_stranger_post_creates_no_row(self, snapshot_animal, second_user_profile, snapshot_dir, client):
        animal, _ = snapshot_animal
        stranger_user, _ = second_user_profile
        client.force_login(stranger_user)

        response = client.post(_rebuild_url(animal))

        assert response.status_code == 403
        assert AnimalSnapshot.objects.count() == 0

    def test_rebuild_with_hx_header_returns_widget_html(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.post(_rebuild_url(animal), headers={"HX-Request": "true"})

        assert response.status_code == 200
        content = response.content.decode()
        assert "offline-snapshot-widget" in content
        assert "Building" in content

    def test_widget_shows_missing_state(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.get(_widget_url(animal))

        assert response.status_code == 200
        assert "Missing" in response.content.decode()


@pytest.mark.integration
class TestSnapshotBuildTask:
    def test_run_build_promotes_to_ready_and_supersedes_previous(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        first = get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        building = request_snapshot_build(animal, profile)

        run_snapshot_build(str(building.id))

        building.refresh_from_db()
        assert building.status == SnapshotStatus.READY
        assert building.is_current is True
        assert building.file_size_bytes > 0
        assert building.build_started_at is not None
        assert building.build_finished_at is not None
        assert snapshot_path(building.storage_key).exists()
        first.refresh_from_db()
        assert first.is_current is False
        assert first.superseded_at is not None

    def test_failed_async_build_leaves_previous_ready_downloadable(
        self, snapshot_animal, snapshot_dir, client, monkeypatch
    ):
        animal, profile = snapshot_animal
        first = get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        building = request_snapshot_build(animal, profile)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        run_snapshot_build(str(building.id))

        building.refresh_from_db()
        assert building.status == SnapshotStatus.FAILED
        assert building.error_message == "boom"
        assert building.is_current is False
        assert building.build_finished_at is not None
        first.refresh_from_db()
        assert first.is_current is True
        client.force_login(profile.user)
        assert client.get(_download_url(animal, first.id)).status_code == 200

    def test_run_build_skips_rows_that_are_not_building(self, snapshot_animal, snapshot_dir, monkeypatch):
        animal, profile = snapshot_animal
        ready = get_or_create_snapshot(animal, profile)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        run_snapshot_build(str(ready.id))

        ready.refresh_from_db()
        assert ready.status == SnapshotStatus.READY
        assert ready.is_current is True

    def test_share_revoked_between_enqueue_and_execution_fails_build(
        self, snapshot_animal, second_user_profile, snapshot_dir
    ):
        animal, _ = snapshot_animal
        _, carer = second_user_profile
        share = AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        building = request_snapshot_build(animal, carer)

        share.delete()
        run_snapshot_build(str(building.id))

        building.refresh_from_db()
        assert building.status == SnapshotStatus.FAILED
        assert "no access" in building.error_message
        assert building.is_current is False


@pytest.mark.integration
class TestManifestWithBuilding:
    def test_manifest_shows_building_without_current(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "building"
        assert manifest["snapshot_id"] == str(building.id)
        assert manifest["download_url"] is None
        assert manifest["building_snapshot_id"] == str(building.id)

    def test_manifest_keeps_ready_current_during_force_rebuild(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)
        building = request_snapshot_build(animal, profile, force=True)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == str(current.id)
        assert manifest["download_url"] == _download_url(animal, current.id)
        assert manifest["building_snapshot_id"] == str(building.id)

        run_snapshot_build(str(building.id))
        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == str(building.id)
        assert manifest["building_snapshot_id"] is None

    def test_manifest_reports_failed_when_nothing_better_exists(self, snapshot_animal, snapshot_dir, client, monkeypatch):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        run_snapshot_build(str(building.id))
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "failed"
        assert manifest["error_message"] == "boom"
        assert manifest["download_url"] is None
        assert manifest["building_snapshot_id"] is None

    def test_download_of_building_snapshot_is_404(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)
        client.force_login(profile.user)

        response = client.get(_download_url(animal, building.id))

        assert response.status_code == 404


@pytest.mark.integration
class TestSnapshotFreshness:
    def test_fresh_ready_manifest_is_not_stale(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["is_stale"] is False
        assert manifest["latest_source_revision"] == manifest["source_revision"]
        assert manifest["can_rebuild"] is False

    def test_animal_field_change_marks_manifest_stale(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["is_stale"] is True
        assert manifest["latest_source_revision"] != manifest["source_revision"]
        assert manifest["can_rebuild"] is True

    def test_feeding_note_change_marks_manifest_stale(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        FeedingNote.objects.update(product_name="Other kibble")
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["is_stale"] is True

    def test_rebuild_restores_freshness(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        building = request_snapshot_build(animal, profile)
        run_snapshot_build(str(building.id))
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["snapshot_id"] == str(building.id)
        assert manifest["is_stale"] is False
        assert manifest["can_rebuild"] is False

    def test_stale_current_stays_downloadable_during_force_rebuild(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        building = request_snapshot_build(animal, profile, force=True)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == str(current.id)
        assert manifest["download_url"] == _download_url(animal, current.id)
        assert manifest["is_stale"] is True
        assert manifest["building_snapshot_id"] == str(building.id)
        assert manifest["can_rebuild"] is False

    def test_carer_freshness_tracks_only_visible_categories(
        self, snapshot_animal, second_user_profile, snapshot_dir, client
    ):
        animal, owner = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        get_or_create_snapshot(animal, carer)
        get_or_create_snapshot(animal, owner)

        VaccinationNote.objects.update(vaccine_name="Rabies v2")

        client.force_login(carer.user)
        assert client.get(_manifest_url(animal)).json()["is_stale"] is False
        client.force_login(owner.user)
        assert client.get(_manifest_url(animal)).json()["is_stale"] is True

        FeedingNote.objects.update(product_name="Other kibble")
        client.force_login(carer.user)
        assert client.get(_manifest_url(animal)).json()["is_stale"] is True

    def test_widget_reports_stale_state_and_refresh_label(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        fresh = client.get(_widget_url(animal)).content.decode()
        assert "Ready, up to date" in fresh
        assert "Generate offline snapshot" in fresh

        animal.dietary_restrictions = "grain only, actually"
        animal.save()

        stale = client.get(_widget_url(animal)).content.decode()
        assert "Ready, but outdated" in stale
        assert "Refresh offline snapshot" in stale


@pytest.mark.integration
class TestPruneStaleBuilding:
    def test_prune_marks_stale_building_failed_and_keeps_fresh(self, snapshot_animal, second_user_profile, snapshot_dir):
        animal, profile = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        stale = request_snapshot_build(animal, profile)
        AnimalSnapshot.objects.filter(id=stale.id).update(generated_at=timezone.now() - timedelta(hours=7))
        fresh = request_snapshot_build(animal, carer)

        call_command("prune_animal_snapshots")

        stale.refresh_from_db()
        assert stale.status == SnapshotStatus.FAILED
        assert "Stale build" in stale.error_message
        assert stale.build_finished_at is not None
        fresh.refresh_from_db()
        assert fresh.status == SnapshotStatus.BUILDING


@pytest.fixture
def snapshot_logs(caplog):
    """Capture app logs despite propagate=False on the ahc.apps.offline_snapshots logger."""
    app_logger = logging.getLogger("ahc.apps.offline_snapshots")
    old_propagate = app_logger.propagate
    app_logger.propagate = True
    caplog.set_level(logging.INFO, logger="ahc.apps.offline_snapshots")
    yield caplog
    app_logger.propagate = old_propagate


@pytest.mark.integration
class TestPruningService:
    def test_service_keeps_current_and_recent_superseded(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        artifacts = [get_or_create_snapshot(animal, profile, force=True) for _ in range(4)]

        result = prune_snapshots(keep=3)

        assert result.deleted_snapshots == 1
        remaining = set(AnimalSnapshot.objects.values_list("id", flat=True))
        assert remaining == {a.id for a in artifacts[1:]}
        assert not snapshot_path(artifacts[0].storage_key).exists()

    def test_service_rejects_invalid_arguments(self):
        with pytest.raises(ValueError, match="keep"):
            prune_snapshots(keep=0)
        with pytest.raises(ValueError, match="download_log_days"):
            prune_snapshots(download_log_days=-1)

    def test_command_maps_invalid_arguments_to_command_error(self, db):
        with pytest.raises(CommandError, match="keep"):
            call_command("prune_animal_snapshots", "--keep", "0")


@pytest.mark.unit
class TestPruneTaskRegistration:
    def test_prune_task_is_in_beat_schedule(self):
        entry = celery_obj.conf.beat_schedule["prune-animal-snapshots-daily"]

        assert entry["task"] == "ahc.offline_snapshots.prune_snapshots"
        assert entry["task"] in celery_obj.tasks

    def test_prune_task_calls_service_with_defaults(self, monkeypatch):
        calls = []
        monkeypatch.setattr(snapshot_tasks, "prune_snapshots", lambda: calls.append(True))

        snapshot_tasks.prune_snapshots_task.run()

        assert calls == [True]


@pytest.mark.integration
class TestBuildLogging:
    def test_successful_build_logs_started_and_finished(self, snapshot_animal, snapshot_dir, snapshot_logs):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)

        run_snapshot_build(str(building.id))

        messages = [record.getMessage() for record in snapshot_logs.records]
        assert any(f"Snapshot build enqueued: snapshot={building.id}" in message for message in messages)
        assert any(f"Snapshot build started: snapshot={building.id}" in message for message in messages)
        assert any(f"Snapshot build finished: snapshot={building.id}" in message for message in messages)

    def test_failed_build_logs_exception_with_traceback(self, snapshot_animal, snapshot_dir, snapshot_logs, monkeypatch):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        run_snapshot_build(str(building.id))

        errors = [record for record in snapshot_logs.records if record.levelno == logging.ERROR]
        assert len(errors) == 1
        assert f"snapshot={building.id}" in errors[0].getMessage()
        assert errors[0].exc_info is not None


@pytest.mark.integration
class TestCheckAnimalSnapshotsCommand:
    def test_healthy_state_reports_no_problems(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        out = StringIO()

        call_command("check_animal_snapshots", stdout=out)

        output = out.getvalue()
        assert "Ready: 1" in output
        assert "No problems found." in output

    def test_reports_broken_current_and_orphans(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        snapshot_path(snapshot.storage_key).unlink()
        (snapshot_dir / "orphan.db").write_bytes(b"stray")
        out = StringIO()

        call_command("check_animal_snapshots", stdout=out)

        output = out.getvalue()
        assert f"Current READY row without file: {snapshot.id}" in output
        assert "Orphaned file (no DB row): orphan.db" in output
        assert "Found 2 problem(s)." in output

    def test_strict_exits_nonzero_on_problems(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        snapshot_path(snapshot.storage_key).unlink()

        with pytest.raises(CommandError, match="1 problem"):
            call_command("check_animal_snapshots", "--strict")

    def test_stale_building_is_reported_not_mutated(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        stale = request_snapshot_build(animal, profile)
        AnimalSnapshot.objects.filter(id=stale.id).update(generated_at=timezone.now() - timedelta(hours=7))
        out = StringIO()

        call_command("check_animal_snapshots", stdout=out)

        assert f"Stale BUILDING: {stale.id}" in out.getvalue()
        stale.refresh_from_db()
        assert stale.status == SnapshotStatus.BUILDING


@pytest.mark.integration
class TestSchemaVersioning:
    def test_model_row_and_manifest_carry_same_schema_version(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)

        (manifest,) = _query(snapshot_path(snapshot.storage_key), "SELECT * FROM snapshot_manifest")

        assert manifest["schema_version"] == snapshot.schema_version == SCHEMA_VERSION

    def test_manifest_carries_exporter_version(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)

        (manifest,) = _query(snapshot_path(snapshot.storage_key), "SELECT exporter_version FROM snapshot_manifest")

        assert manifest["exporter_version"] == EXPORTER_VERSION


@pytest.mark.unit
def test_schema_version_bump_is_deliberate():
    # Bumping SCHEMA_VERSION is a breaking change for every snapshot reader.
    # Re-read the compatibility contract in ADR-12 (stage 5) before touching
    # this assertion: additive changes must NOT bump the version.
    assert SCHEMA_VERSION == 1


@pytest.mark.integration
class TestDownloadAuditTrail:
    def test_successful_download_is_recorded(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        response = client.get(_download_url(animal, snapshot.id))

        assert response.status_code == 200
        log = SnapshotDownloadLog.objects.get()
        assert log.outcome == DownloadOutcome.SUCCESS
        assert log.animal == animal
        assert log.profile == profile
        assert log.snapshot == snapshot

    def test_forbidden_download_is_recorded_without_snapshot(
        self, snapshot_animal, second_user_profile, snapshot_dir, client
    ):
        animal, owner = snapshot_animal
        snapshot = get_or_create_snapshot(animal, owner)
        stranger_user, stranger = second_user_profile
        client.force_login(stranger_user)

        response = client.get(_download_url(animal, snapshot.id))

        assert response.status_code == 403
        log = SnapshotDownloadLog.objects.get()
        assert log.outcome == DownloadOutcome.FORBIDDEN
        assert log.profile == stranger
        assert log.snapshot is None

    def test_unknown_snapshot_id_is_recorded_as_not_found(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.get(_download_url(animal, uuid.uuid4()))

        assert response.status_code == 404
        log = SnapshotDownloadLog.objects.get()
        assert log.outcome == DownloadOutcome.NOT_FOUND
        assert log.snapshot is None

    def test_missing_file_is_recorded_with_snapshot_row(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        snapshot_path(snapshot.storage_key).unlink()
        client.force_login(profile.user)

        response = client.get(_download_url(animal, snapshot.id))

        assert response.status_code == 404
        log = SnapshotDownloadLog.objects.get()
        assert log.outcome == DownloadOutcome.NOT_FOUND
        assert log.snapshot == snapshot

    def test_audit_row_outlives_deleted_snapshot(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)
        client.get(_download_url(animal, snapshot.id))

        snapshot.delete()

        log = SnapshotDownloadLog.objects.get()
        assert log.outcome == DownloadOutcome.SUCCESS
        assert log.snapshot is None

    def test_prune_trims_old_download_logs(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        old = SnapshotDownloadLog.objects.create(animal=animal, profile=profile, outcome=DownloadOutcome.SUCCESS)
        SnapshotDownloadLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=91))
        recent = SnapshotDownloadLog.objects.create(animal=animal, profile=profile, outcome=DownloadOutcome.SUCCESS)

        result = prune_snapshots(download_log_days=90)

        assert result.deleted_download_logs == 1
        assert set(SnapshotDownloadLog.objects.values_list("pk", flat=True)) == {recent.pk}


@pytest.mark.integration
class TestInspectCommand:
    def test_reports_manifest_and_row_counts(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), stdout=out)

        output = out.getvalue()
        assert str(animal.id) in output
        assert f"Schema version: {SCHEMA_VERSION}" in output
        assert f"Exporter version: {EXPORTER_VERSION}" in output
        assert "medical_record_snapshot: 5" in output
        assert "Snapshot OK" in output

    def test_json_output(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), "--json", stdout=out)

        report = json.loads(out.getvalue())
        assert report["animal_id"] == str(animal.id)
        assert report["schema_version"] == SCHEMA_VERSION
        assert report["exporter_version"] == EXPORTER_VERSION
        assert report["is_read_only"] is True
        assert len(report["source_revision"]) == 64
        assert report["row_counts"] == {
            "animal_snapshot": 1,
            "medical_record_snapshot": 5,
            "feeding_note_snapshot": 1,
            "biometric_snapshot": 1,
            "vaccination_note_snapshot": 1,
            "attachment_metadata_snapshot": 1,
        }

    def test_unsupported_schema_version_raises_command_error(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        conn = sqlite3.connect(path)
        conn.execute("UPDATE snapshot_manifest SET schema_version = 999")
        conn.commit()
        conn.close()

        with pytest.raises(CommandError, match="Unsupported schema_version 999"):
            call_command("inspect_animal_snapshot", str(path))


@pytest.mark.unit
class TestInspectCommandBrokenFiles:
    def test_missing_file_raises_command_error(self, tmp_path):
        with pytest.raises(CommandError, match="File not found"):
            call_command("inspect_animal_snapshot", str(tmp_path / "nope.db"))

    def test_corrupted_file_raises_command_error(self, tmp_path):
        junk = tmp_path / "junk.db"
        junk.write_bytes(b"this is not a sqlite database")

        with pytest.raises(CommandError, match="Not a valid SQLite snapshot"):
            call_command("inspect_animal_snapshot", str(junk))

    def test_sqlite_file_without_manifest_raises_command_error(self, tmp_path):
        empty = tmp_path / "empty.db"
        conn = sqlite3.connect(empty)
        conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        with pytest.raises(CommandError, match="Not a valid SQLite snapshot"):
            call_command("inspect_animal_snapshot", str(empty))

    def test_accepts_stage4_snapshot_without_exporter_version(self, tmp_path):
        path = tmp_path / "old.db"
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE snapshot_manifest (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                animal_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                source_revision TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                generated_by TEXT,
                is_read_only INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        for ddl in TABLES[1:]:
            conn.execute(ddl)
        conn.execute(
            "INSERT INTO snapshot_manifest (id, animal_id, schema_version, source_revision, generated_at)"
            " VALUES (1, ?, ?, ?, ?)",
            (str(uuid.uuid4()), SCHEMA_VERSION, "a" * 64, "2026-05-01T12:00:00+00:00"),
        )
        conn.commit()
        conn.close()
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), "--json", stdout=out)

        report = json.loads(out.getvalue())
        assert report["exporter_version"] is None
        assert report["schema_version"] == SCHEMA_VERSION
