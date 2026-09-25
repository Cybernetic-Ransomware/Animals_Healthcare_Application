import pytest

from ahc.apps.animals.models import AnimalShare
from ahc.apps.offline_snapshots import tasks as snapshot_tasks
from ahc.apps.offline_snapshots.models import SnapshotStatus
from ahc.apps.offline_snapshots.services import lifecycle
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    request_snapshot_build,
    run_snapshot_build,
)
from ahc.apps.offline_snapshots.services.storage import snapshot_path
from celery_notifications.config import celery_obj

from .helpers import _download_url


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
