"""Celery tasks for asynchronous snapshot builds and retention (ADR-12, stages 3 and 5).

Tasks are deliberately thin wrappers: all logic lives in services.lifecycle
and services.pruning so it stays testable without a broker. Importing
celery_obj here (instead of using a bare shared_task) also configures the
Celery app inside the web process, so .apply_async() from views talks to the
real broker rather than Celery's unconfigured default app.
"""

from ahc.apps.offline_snapshots.services.lifecycle import run_snapshot_build
from ahc.apps.offline_snapshots.services.pruning import prune_snapshots
from celery_notifications.config import celery_obj


@celery_obj.task(bind=True, name="ahc.offline_snapshots.build_snapshot")
def build_snapshot_task(self, snapshot_id: str) -> None:
    run_snapshot_build(snapshot_id)


@celery_obj.task(name="ahc.offline_snapshots.prune_snapshots")
def prune_snapshots_task() -> None:
    # Defaults only: ops overrides go through the prune_animal_snapshots
    # management command, not through beat payloads. Exceptions propagate so
    # the worker log and Flower record a failed run.
    prune_snapshots()
