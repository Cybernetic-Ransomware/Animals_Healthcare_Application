"""Celery task for asynchronous snapshot builds (ADR-12, stage 3).

The task is deliberately a thin wrapper: all build logic lives in
services.lifecycle.run_snapshot_build so it stays testable without a broker.
Importing celery_obj here (instead of using a bare shared_task) also configures
the Celery app inside the web process, so .apply_async() from views talks to
the real broker rather than Celery's unconfigured default app.
"""

from ahc.apps.offline_snapshots.services.lifecycle import run_snapshot_build
from celery_notifications.config import celery_obj


@celery_obj.task(bind=True, name="ahc.offline_snapshots.build_snapshot")
def build_snapshot_task(self, snapshot_id: str) -> None:
    run_snapshot_build(snapshot_id)
