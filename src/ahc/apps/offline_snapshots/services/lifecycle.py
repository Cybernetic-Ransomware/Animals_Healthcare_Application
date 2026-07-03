"""Snapshot lifecycle: revision-gated get-or-rebuild over immutable artifacts.

Two entry points share the same contract (ADR-12, stages 2-3): a failed build
is recorded as a FAILED artifact row and the previous current artifact stays
untouched and downloadable. get_or_create_snapshot builds synchronously (CLI,
tests); request_snapshot_build creates a BUILDING row and delegates the actual
build to the Celery task, which calls run_snapshot_build.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.exporter import ExportPlan, build_export_plan, write_snapshot_file
from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION
from ahc.apps.offline_snapshots.services.storage import build_snapshot_storage_key, snapshot_path

if TYPE_CHECKING:
    from ahc.apps.animals.models import Animal
    from ahc.apps.users.models import Profile


def current_snapshot_for(animal: Animal, profile: Profile) -> AnimalSnapshot | None:
    # status=READY is defensive: _promote_to_current sets READY and is_current
    # together, but the partial unique constraint alone does not enforce it.
    return AnimalSnapshot.objects.filter(
        animal=animal,
        generated_for=profile,
        status=SnapshotStatus.READY,
        is_current=True,
    ).first()


def active_building_snapshot_for(animal: Animal, profile: Profile) -> AnimalSnapshot | None:
    return (
        AnimalSnapshot.objects.filter(animal=animal, generated_for=profile, status=SnapshotStatus.BUILDING)
        .order_by("-generated_at")
        .first()
    )


def snapshot_freshness_for(animal: Animal, profile: Profile, current: AnimalSnapshot | None) -> dict | None:
    """Compare the current READY artifact against the live payload revision.

    Returns None when there is nothing READY to compare against. The plan is
    profile-scoped, so a carer's freshness reflects only the data they may
    see: a change in a category hidden from them does not mark their snapshot
    stale. Raises PermissionDenied when the profile may not view the animal.
    """
    if current is None or current.status != SnapshotStatus.READY:
        return None
    plan = build_export_plan(animal, profile)
    return {
        "latest_source_revision": plan.source_revision,
        "is_stale": current.source_revision != plan.source_revision,
    }


def _new_building_snapshot(animal: Animal, profile: Profile, plan: ExportPlan) -> AnimalSnapshot:
    snapshot = AnimalSnapshot(
        animal=animal,
        generated_for=profile,
        schema_version=SCHEMA_VERSION,
        source_revision=plan.source_revision,
        allowed_categories_json=plan.allowed_categories,
    )
    snapshot.storage_key = build_snapshot_storage_key(snapshot.id)
    return snapshot


def _mark_failed(snapshot: AnimalSnapshot, exc: Exception) -> None:
    snapshot.status = SnapshotStatus.FAILED
    snapshot.error_message = str(exc)[:2500]
    snapshot.build_finished_at = timezone.now()
    snapshot.save(update_fields=["status", "error_message", "build_finished_at"])


def _promote_to_current(snapshot: AnimalSnapshot, plan: ExportPlan) -> None:
    """Flip is_current to the freshly written artifact; the file must already exist on disk."""
    with transaction.atomic():
        AnimalSnapshot.objects.filter(animal=snapshot.animal, generated_for=snapshot.generated_for, is_current=True).update(
            is_current=False, superseded_at=timezone.now()
        )
        snapshot.file_size_bytes = snapshot_path(snapshot.storage_key).stat().st_size
        snapshot.source_revision = plan.source_revision
        snapshot.allowed_categories_json = plan.allowed_categories
        snapshot.status = SnapshotStatus.READY
        snapshot.is_current = True
        snapshot.build_finished_at = timezone.now()
        snapshot.save()


def get_or_create_snapshot(animal: Animal, profile: Profile, force: bool = False) -> AnimalSnapshot:
    """Return the current snapshot for (animal, profile), rebuilding synchronously when needed.

    Raises PermissionDenied when the profile may not view the animal. A build
    failure is recorded as a FAILED artifact row and returned; the previous
    current artifact stays untouched and downloadable.
    """
    plan = build_export_plan(animal, profile)

    current = current_snapshot_for(animal, profile)
    if (
        current is not None
        and not force
        and current.source_revision == plan.source_revision
        and snapshot_path(current.storage_key).exists()
    ):
        return current

    snapshot = _new_building_snapshot(animal, profile, plan)
    snapshot.build_started_at = timezone.now()
    snapshot.save()

    try:
        write_snapshot_file(animal, profile, plan, snapshot_path(snapshot.storage_key))
    except Exception as exc:
        _mark_failed(snapshot, exc)
        return snapshot

    _promote_to_current(snapshot, plan)
    return snapshot


def request_snapshot_build(animal: Animal, profile: Profile, force: bool = False) -> AnimalSnapshot:
    """Return a READY current snapshot or a BUILDING one with a Celery build enqueued.

    Raises PermissionDenied when the profile may not view the animal. force
    bypasses only the revision-freshness check on the current snapshot; an
    already-active BUILDING row is always reused so repeated requests cannot
    stack parallel builds of the same pair.
    """
    plan = build_export_plan(animal, profile)

    current = current_snapshot_for(animal, profile)
    if (
        current is not None
        and not force
        and current.source_revision == plan.source_revision
        and snapshot_path(current.storage_key).exists()
    ):
        return current

    with transaction.atomic():
        building = (
            AnimalSnapshot.objects.select_for_update()
            .filter(animal=animal, generated_for=profile, status=SnapshotStatus.BUILDING)
            .order_by("-generated_at")
            .first()
        )
        if building is not None:
            return building

        snapshot = _new_building_snapshot(animal, profile, plan)
        snapshot.task_id = str(uuid.uuid4())
        snapshot.save()

    from ahc.apps.offline_snapshots.tasks import build_snapshot_task  # local import: tasks.py imports this module

    transaction.on_commit(lambda: build_snapshot_task.apply_async(args=[str(snapshot.id)], task_id=snapshot.task_id))
    return snapshot


def run_snapshot_build(snapshot_id: str) -> None:
    """Execute one queued build attempt; safe to call more than once per row.

    Rows that are missing or no longer BUILDING are skipped, so a duplicated or
    retried task cannot rewrite a finished artifact. Data and permissions are
    re-read at execution time: the export plan is rebuilt from scratch and a
    revoked share surfaces as a FAILED row, never as a stale export.
    """
    snapshot = (
        AnimalSnapshot.objects.select_related("animal", "generated_for")
        .filter(id=snapshot_id, status=SnapshotStatus.BUILDING)
        .first()
    )
    if snapshot is None:
        return

    snapshot.build_started_at = timezone.now()
    snapshot.save(update_fields=["build_started_at"])

    try:
        plan = build_export_plan(snapshot.animal, snapshot.generated_for)
        write_snapshot_file(snapshot.animal, snapshot.generated_for, plan, snapshot_path(snapshot.storage_key))
    except Exception as exc:
        _mark_failed(snapshot, exc)
        return

    _promote_to_current(snapshot, plan)
