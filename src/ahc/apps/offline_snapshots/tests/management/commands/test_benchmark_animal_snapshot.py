import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.integration
class TestBenchmarkCommand:
    def test_outputs_valid_json(self, snapshot_animal, tmp_path):
        animal, _ = snapshot_animal
        out = StringIO()

        call_command("benchmark_animal_snapshot", str(animal.id), "--runs", "1", "--json", stdout=out)

        report = json.loads(out.getvalue())
        assert report["animal_id"] == str(animal.id)
        assert report["runs"] == 1
        assert report["file_size_bytes"] > 0
        assert set(report["phases"]) == {
            "build_export_plan",
            "write_snapshot_file",
            "inspect_sqlite3",
            "read_snapshot_libsql",
            "compare_drivers",
        }
        for phase_stats in report["phases"].values():
            assert "min_ms" in phase_stats
            assert "mean_ms" in phase_stats
            assert "max_ms" in phase_stats

    def test_rejects_zero_runs(self, snapshot_animal):
        animal, _ = snapshot_animal

        with pytest.raises(CommandError, match="--runs must be at least 1"):
            call_command("benchmark_animal_snapshot", str(animal.id), "--runs", "0")
