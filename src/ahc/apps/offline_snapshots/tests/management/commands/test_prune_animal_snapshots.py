from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from ahc.apps.animals.models import AnimalShare
from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services import lifecycle
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    request_snapshot_build,
)
from ahc.apps.offline_snapshots.services.storage import snapshot_path


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
