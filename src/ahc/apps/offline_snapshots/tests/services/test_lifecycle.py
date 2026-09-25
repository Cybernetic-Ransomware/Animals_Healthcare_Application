import logging

import pytest
from django.core.exceptions import PermissionDenied

from ahc.apps.animals.models import AnimalShare, ShareCategory
from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services import lifecycle
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    request_snapshot_build,
    run_snapshot_build,
)
from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION
from ahc.apps.offline_snapshots.services.storage import snapshot_path

from ..helpers import _query


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
