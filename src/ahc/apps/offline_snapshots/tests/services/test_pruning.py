import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ahc.apps.offline_snapshots.models import AnimalSnapshot
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
)
from ahc.apps.offline_snapshots.services.pruning import prune_snapshots
from ahc.apps.offline_snapshots.services.storage import snapshot_path


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
