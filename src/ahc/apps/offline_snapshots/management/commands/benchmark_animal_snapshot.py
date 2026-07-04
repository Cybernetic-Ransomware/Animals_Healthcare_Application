import json
import statistics
import tempfile
import time
from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import profile_by_username
from ahc.apps.offline_snapshots.services.driver_parity import compare_drivers, read_snapshot_libsql
from ahc.apps.offline_snapshots.services.exporter import build_export_plan, write_snapshot_file
from ahc.apps.offline_snapshots.services.inspector import inspect_snapshot


def _stats(times: list[float]) -> dict[str, float]:
    return {
        "min_ms": min(times),
        "mean_ms": statistics.mean(times),
        "max_ms": max(times),
    }


class Command(BaseCommand):
    help = "Diagnostic benchmark of the offline snapshot pipeline phases. Not a CI gate — no time assertions."

    def add_arguments(self, parser):
        parser.add_argument("animal_id", help="UUID of the animal to benchmark")
        parser.add_argument("--runs", type=int, default=3, help="Number of timed iterations (default: 3)")
        parser.add_argument("--username", default=None, help="Run as this user (default: animal owner)")
        parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON instead of a table")

    def handle(self, *args, **options):
        try:
            animal = Animal.objects.get(pk=options["animal_id"])
        except (Animal.DoesNotExist, ValidationError, ValueError) as exc:
            raise CommandError(f"No animal found for id '{options['animal_id']}'.") from exc

        if options["username"]:
            profile = profile_by_username(options["username"])
            if profile is None:
                raise CommandError(f"No profile found for username '{options['username']}'.")
        else:
            profile = animal.owner
            if profile is None:
                raise CommandError("Animal has no owner; pass --username to benchmark as a specific user.")

        runs = options["runs"]
        if runs < 1:
            raise CommandError("--runs must be at least 1.")

        results: dict[str, dict] = {}

        # Phase 1: build_export_plan — pure Python + DB query, no file I/O.
        # Build once outside the loop to validate permissions and establish the
        # ExportPlan type; then time N iterations without re-catching PermissionDenied
        # (the profile cannot flip permissions mid-command).
        try:
            plan = build_export_plan(animal, profile)
        except PermissionDenied as exc:
            raise CommandError(str(exc)) from exc

        plan_times: list[float] = []
        for _ in range(runs):
            t0 = time.perf_counter()
            plan = build_export_plan(animal, profile)
            plan_times.append((time.perf_counter() - t0) * 1000)
        results["build_export_plan"] = _stats(plan_times)

        # Phases 2-5: require a file on disk — fresh path per run so write timings
        # are not skewed by SQLite page-cache warmup across iterations.
        write_times: list[float] = []
        sqlite3_times: list[float] = []
        libsql_times: list[float] = []
        compare_times: list[float] = []
        file_size_bytes: int | None = None
        row_counts: dict | None = None

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(runs):
                dest = Path(tmpdir) / f"bench_{i}.db"

                t0 = time.perf_counter()
                write_snapshot_file(animal, profile, plan, dest)
                write_times.append((time.perf_counter() - t0) * 1000)

                if i == runs - 1:
                    file_size_bytes = dest.stat().st_size

                t0 = time.perf_counter()
                report = inspect_snapshot(dest)
                sqlite3_times.append((time.perf_counter() - t0) * 1000)

                if i == runs - 1:
                    row_counts = report.get("row_counts")

                t0 = time.perf_counter()
                read_snapshot_libsql(dest)
                libsql_times.append((time.perf_counter() - t0) * 1000)

                t0 = time.perf_counter()
                compare_drivers(dest)
                compare_times.append((time.perf_counter() - t0) * 1000)

        results["write_snapshot_file"] = _stats(write_times)
        results["inspect_sqlite3"] = _stats(sqlite3_times)
        results["read_snapshot_libsql"] = _stats(libsql_times)
        results["compare_drivers"] = _stats(compare_times)

        if options["as_json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "animal_id": str(animal.id),
                        "runs": runs,
                        "file_size_bytes": file_size_bytes,
                        "row_counts": row_counts,
                        "phases": results,
                    },
                    indent=2,
                )
            )
        else:
            self._print_table(animal, runs, file_size_bytes, row_counts, results)

    def _print_table(self, animal, runs, file_size_bytes, row_counts, results):
        self.stdout.write(f"\nBenchmark — animal={animal.id}  runs={runs}\n")
        self.stdout.write(f"{'Phase':<28} {'min_ms':>8} {'mean_ms':>8} {'max_ms':>8}\n")
        self.stdout.write("-" * 56 + "\n")
        for phase, stats in results.items():
            self.stdout.write(f"{phase:<28} {stats['min_ms']:>8.1f} {stats['mean_ms']:>8.1f} {stats['max_ms']:>8.1f}\n")
        self.stdout.write(f"\nfile_size_bytes: {file_size_bytes}\n")
        if row_counts:
            counts_str = ", ".join(f"{t}={n}" for t, n in row_counts.items())
            self.stdout.write(f"row_counts: {counts_str}\n")
