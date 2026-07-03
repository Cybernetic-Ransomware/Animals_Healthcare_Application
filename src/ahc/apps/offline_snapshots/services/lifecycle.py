"""Snapshot lifecycle: revision-gated get-or-rebuild over immutable artifacts.

Synchronous for now; the BUILDING/FAILED statuses keep the contract ready for
a future Celery task without any model change (see ADR-12, stage 2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.exporter import build_export_plan, write_snapshot_file
from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION
from ahc.apps.offline_snapshots.services.storage import build_snapshot_storage_key, snapshot_path

if TYPE_CHECKING:
    from ahc.apps.animals.models import Animal
    from ahc.apps.users.models import Profile


def current_snapshot_for(animal: Animal, profile: Profile) -> AnimalSnapshot | None:
    return AnimalSnapshot.objects.filter(animal=animal, generated_for=profile, is_current=True).first()


def get_or_create_snapshot(animal: Animal, profile: Profile, force: bool = False) -> AnimalSnapshot:
    """Return the current snapshot for (animal, profile), rebuilding only when needed.

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

    snapshot = AnimalSnapshot(
        animal=animal,
        generated_for=profile,
        schema_version=SCHEMA_VERSION,
        source_revision=plan.source_revision,
        allowed_categories_json=plan.allowed_categories,
    )
    snapshot.storage_key = build_snapshot_storage_key(snapshot.id)
    snapshot.save()

    final_path = snapshot_path(snapshot.storage_key)
    try:
        write_snapshot_file(animal, profile, plan, final_path)
    except Exception as exc:
        snapshot.status = SnapshotStatus.FAILED
        snapshot.error_message = str(exc)[:2500]
        snapshot.save(update_fields=["status", "error_message"])
        return snapshot

    with transaction.atomic():
        AnimalSnapshot.objects.filter(animal=animal, generated_for=profile, is_current=True).update(
            is_current=False, superseded_at=timezone.now()
        )
        snapshot.file_size_bytes = final_path.stat().st_size
        snapshot.status = SnapshotStatus.READY
        snapshot.is_current = True
        snapshot.save()
    return snapshot
