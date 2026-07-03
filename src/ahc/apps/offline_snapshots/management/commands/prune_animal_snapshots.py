from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.storage import snapshot_path


class Command(BaseCommand):
    help = "Delete superseded snapshot artifacts and stale failed/building rows (see ADR-12, stages 2-3)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep", type=int, default=3, help="Snapshots to keep per animal/profile pair, current included (default: 3)"
        )
        parser.add_argument(
            "--failed-days", type=int, default=7, help="Delete FAILED rows older than this many days (default: 7)"
        )
        parser.add_argument(
            "--stale-building-hours",
            type=int,
            default=6,
            help="Mark BUILDING rows older than this many hours as FAILED (default: 6)",
        )

    def handle(self, *args, **options):
        keep = options["keep"]
        failed_days = options["failed_days"]
        stale_building_hours = options["stale_building_hours"]
        if keep < 1:
            raise CommandError("--keep must be at least 1.")
        if failed_days < 0:
            raise CommandError("--failed-days must not be negative.")
        if stale_building_hours < 0:
            raise CommandError("--stale-building-hours must not be negative.")

        failed = self._fail_stale_building(stale_building_hours)
        deleted = self._prune_superseded(keep) + self._prune_failed(failed_days)
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} snapshot(s), failed {failed} stale build(s)."))

    def _fail_stale_building(self, stale_building_hours: int) -> int:
        cutoff = timezone.now() - timedelta(hours=stale_building_hours)
        return AnimalSnapshot.objects.filter(status=SnapshotStatus.BUILDING, generated_at__lt=cutoff).update(
            status=SnapshotStatus.FAILED,
            error_message="Stale build: worker never finished.",
            build_finished_at=timezone.now(),
        )

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
