from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.storage import snapshot_path


class Command(BaseCommand):
    help = "Delete superseded snapshot artifacts and stale failed build rows (see ADR-12, stage 2)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep", type=int, default=3, help="Snapshots to keep per animal/profile pair, current included (default: 3)"
        )
        parser.add_argument(
            "--failed-days", type=int, default=7, help="Delete FAILED rows older than this many days (default: 7)"
        )

    def handle(self, *args, **options):
        keep = options["keep"]
        failed_days = options["failed_days"]
        if keep < 1:
            raise CommandError("--keep must be at least 1.")
        if failed_days < 0:
            raise CommandError("--failed-days must not be negative.")

        deleted = self._prune_superseded(keep) + self._prune_failed(failed_days)
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} snapshot(s)."))

    def _prune_superseded(self, keep: int) -> int:
        deleted = 0
        pairs = AnimalSnapshot.objects.values_list("animal_id", "generated_for_id").distinct()
        for animal_id, profile_id in pairs:
            stale = AnimalSnapshot.objects.filter(
                animal_id=animal_id,
                generated_for_id=profile_id,
                status=SnapshotStatus.READY,
                is_current=False,
            ).order_by("-generated_at")[keep - 1 :]
            deleted += sum(self._delete_snapshot(snapshot) for snapshot in stale)
        return deleted

    def _prune_failed(self, failed_days: int) -> int:
        cutoff = timezone.now() - timedelta(days=failed_days)
        stale = AnimalSnapshot.objects.filter(status=SnapshotStatus.FAILED, generated_at__lt=cutoff)
        return sum(self._delete_snapshot(snapshot) for snapshot in stale)

    def _delete_snapshot(self, snapshot: AnimalSnapshot) -> int:
        snapshot_path(snapshot.storage_key).unlink(missing_ok=True)
        snapshot.delete()
        return 1
