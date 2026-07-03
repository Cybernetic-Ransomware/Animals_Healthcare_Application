from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.storage import snapshot_path


class Command(BaseCommand):
    help = "Read-only health report for offline snapshots: status counts, stale builds, broken/orphaned files (ADR-12)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stale-building-hours",
            type=int,
            default=6,
            help="Report BUILDING rows older than this many hours (default: 6); rows are never mutated",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit non-zero when stale builds, broken current rows or orphaned files are found",
        )

    def handle(self, *args, **options):
        counts = dict(AnimalSnapshot.objects.values_list("status").annotate(n=Count("id")))
        current_count = AnimalSnapshot.objects.filter(is_current=True).count()
        self.stdout.write("Snapshot rows by status:")
        for status in SnapshotStatus:
            self.stdout.write(f"  {status.label}: {counts.get(status.value, 0)}")
        self.stdout.write(f"  Current: {current_count}")

        cutoff = timezone.now() - timedelta(hours=options["stale_building_hours"])
        stale_building = list(AnimalSnapshot.objects.filter(status=SnapshotStatus.BUILDING, generated_at__lt=cutoff))
        for snapshot in stale_building:
            age_hours = (timezone.now() - snapshot.generated_at).total_seconds() / 3600
            self.stdout.write(self.style.WARNING(f"Stale BUILDING: {snapshot.id} (age: {age_hours:.1f}h)"))

        broken_current = [
            snapshot
            for snapshot in AnimalSnapshot.objects.filter(status=SnapshotStatus.READY, is_current=True)
            if not snapshot_path(snapshot.storage_key).exists()
        ]
        for snapshot in broken_current:
            self.stdout.write(self.style.WARNING(f"Current READY row without file: {snapshot.id}"))

        orphans, total_bytes = self._scan_snapshot_root()
        for orphan in orphans:
            self.stdout.write(self.style.WARNING(f"Orphaned file (no DB row): {orphan.name}"))
        self.stdout.write(f"Snapshot root disk usage: {total_bytes} bytes")

        problems = len(stale_building) + len(broken_current) + len(orphans)
        if problems == 0:
            self.stdout.write(self.style.SUCCESS("No problems found."))
        elif options["strict"]:
            raise CommandError(f"Found {problems} problem(s): see report above.")
        else:
            self.stdout.write(self.style.WARNING(f"Found {problems} problem(s)."))

    def _scan_snapshot_root(self) -> tuple[list[Path], int]:
        root = Path(settings.OFFLINE_SNAPSHOT_ROOT)
        if not root.is_dir():
            self.stdout.write("Snapshot root does not exist yet (no files written).")
            return [], 0
        known_keys = set(AnimalSnapshot.objects.values_list("storage_key", flat=True))
        orphans = []
        total_bytes = 0
        for file in sorted(root.glob("*.db")):
            total_bytes += file.stat().st_size
            if file.name not in known_keys:
                orphans.append(file)
        return orphans, total_bytes
