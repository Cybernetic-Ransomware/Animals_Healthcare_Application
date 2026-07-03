"""Snapshot retention: delete superseded artifacts and stale failed/building rows.

Extracted from the prune_animal_snapshots management command (ADR-12, stage 5)
so the same logic runs from the CLI wrapper and the daily Celery Beat task
without going through call_command.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotDownloadLog, SnapshotStatus
from ahc.apps.offline_snapshots.services.storage import snapshot_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PruneResult:
    deleted_snapshots: int
    failed_stale_builds: int
    deleted_download_logs: int


def prune_snapshots(
    keep: int = 3, failed_days: int = 7, stale_building_hours: int = 6, download_log_days: int = 90
) -> PruneResult:
    """Run one full retention pass; validates arguments for any caller.

    keep counts READY snapshots retained per (animal, generated_for) pair,
    current included. Raises ValueError on out-of-range arguments.
    """
    if keep < 1:
        raise ValueError("keep must be at least 1.")
    if failed_days < 0:
        raise ValueError("failed_days must not be negative.")
    if stale_building_hours < 0:
        raise ValueError("stale_building_hours must not be negative.")
    if download_log_days < 0:
        raise ValueError("download_log_days must not be negative.")

    failed = _fail_stale_building(stale_building_hours)
    deleted = _prune_superseded(keep) + _prune_failed(failed_days)
    logs_deleted = _prune_download_logs(download_log_days)
    result = PruneResult(deleted_snapshots=deleted, failed_stale_builds=failed, deleted_download_logs=logs_deleted)
    logger.info(
        "Snapshot prune finished: deleted=%s stale_failed=%s logs_deleted=%s",
        result.deleted_snapshots,
        result.failed_stale_builds,
        result.deleted_download_logs,
    )
    return result


def _fail_stale_building(stale_building_hours: int) -> int:
    cutoff = timezone.now() - timedelta(hours=stale_building_hours)
    return AnimalSnapshot.objects.filter(status=SnapshotStatus.BUILDING, generated_at__lt=cutoff).update(
        status=SnapshotStatus.FAILED,
        error_message="Stale build: worker never finished.",
        build_finished_at=timezone.now(),
    )


def _prune_superseded(keep: int) -> int:
    deleted = 0
    pairs = AnimalSnapshot.objects.values_list("animal_id", "generated_for_id").distinct()
    for animal_id, profile_id in pairs:
        stale = AnimalSnapshot.objects.filter(
            animal_id=animal_id,
            generated_for_id=profile_id,
            status=SnapshotStatus.READY,
            is_current=False,
        ).order_by("-generated_at")[keep - 1 :]
        deleted += sum(_delete_snapshot(snapshot) for snapshot in stale)
    return deleted


def _prune_failed(failed_days: int) -> int:
    cutoff = timezone.now() - timedelta(days=failed_days)
    stale = AnimalSnapshot.objects.filter(status=SnapshotStatus.FAILED, generated_at__lt=cutoff)
    return sum(_delete_snapshot(snapshot) for snapshot in stale)


def _prune_download_logs(download_log_days: int) -> int:
    cutoff = timezone.now() - timedelta(days=download_log_days)
    deleted, _ = SnapshotDownloadLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def _delete_snapshot(snapshot: AnimalSnapshot) -> int:
    snapshot_path(snapshot.storage_key).unlink(missing_ok=True)
    snapshot.delete()
    return 1
