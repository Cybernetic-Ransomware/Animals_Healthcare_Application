from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    request_snapshot_build,
)
from ahc.apps.offline_snapshots.services.storage import snapshot_path


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
