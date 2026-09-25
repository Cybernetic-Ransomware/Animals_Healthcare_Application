import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from ahc.apps.offline_snapshots.models import DownloadOutcome, SnapshotDownloadLog
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
)
from ahc.apps.offline_snapshots.services.pruning import prune_snapshots
from ahc.apps.offline_snapshots.services.storage import snapshot_path

from ..helpers import _download_url


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
