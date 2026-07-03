from django.core.management.base import BaseCommand, CommandError

from ahc.apps.offline_snapshots.services.pruning import prune_snapshots


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
        parser.add_argument(
            "--download-log-days",
            type=int,
            default=90,
            help="Delete download audit rows older than this many days (default: 90)",
        )

    def handle(self, *args, **options):
        try:
            result = prune_snapshots(
                keep=options["keep"],
                failed_days=options["failed_days"],
                stale_building_hours=options["stale_building_hours"],
                download_log_days=options["download_log_days"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {result.deleted_snapshots} snapshot(s), failed {result.failed_stale_builds} stale build(s),"
                f" deleted {result.deleted_download_logs} download log(s)."
            )
        )
