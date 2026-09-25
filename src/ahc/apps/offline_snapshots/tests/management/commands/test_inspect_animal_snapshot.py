import json
import sqlite3
import uuid
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ahc.apps.offline_snapshots.services.exporter import export_animal_snapshot
from ahc.apps.offline_snapshots.services.schema import EXPORTER_VERSION, SCHEMA_VERSION, TABLES


@pytest.mark.integration
class TestInspectCommand:
    def test_reports_manifest_and_row_counts(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), stdout=out)

        output = out.getvalue()
        assert str(animal.id) in output
        assert f"Schema version: {SCHEMA_VERSION}" in output
        assert f"Exporter version: {EXPORTER_VERSION}" in output
        assert "medical_record_snapshot: 5" in output
        assert "Snapshot OK" in output

    def test_json_output(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), "--json", stdout=out)

        report = json.loads(out.getvalue())
        assert report["animal_id"] == str(animal.id)
        assert report["schema_version"] == SCHEMA_VERSION
        assert report["exporter_version"] == EXPORTER_VERSION
        assert report["is_read_only"] is True
        assert len(report["source_revision"]) == 64
        assert report["row_counts"] == {
            "animal_snapshot": 1,
            "medical_record_snapshot": 5,
            "feeding_note_snapshot": 1,
            "biometric_snapshot": 1,
            "vaccination_note_snapshot": 1,
            "attachment_metadata_snapshot": 1,
        }

    def test_unsupported_schema_version_raises_command_error(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        conn = sqlite3.connect(path)
        conn.execute("UPDATE snapshot_manifest SET schema_version = 999")
        conn.commit()
        conn.close()

        with pytest.raises(CommandError, match="Unsupported schema_version 999"):
            call_command("inspect_animal_snapshot", str(path))


@pytest.mark.integration
class TestInspectCommandBrokenFiles:
    def test_missing_file_raises_command_error(self, tmp_path):
        with pytest.raises(CommandError, match="File not found"):
            call_command("inspect_animal_snapshot", str(tmp_path / "nope.db"))

    def test_corrupted_file_raises_command_error(self, tmp_path):
        junk = tmp_path / "junk.db"
        junk.write_bytes(b"this is not a sqlite database")

        with pytest.raises(CommandError, match="Not a valid SQLite snapshot"):
            call_command("inspect_animal_snapshot", str(junk))

    def test_sqlite_file_without_manifest_raises_command_error(self, tmp_path):
        empty = tmp_path / "empty.db"
        conn = sqlite3.connect(empty)
        conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        with pytest.raises(CommandError, match="Not a valid SQLite snapshot"):
            call_command("inspect_animal_snapshot", str(empty))

    def test_accepts_stage4_snapshot_without_exporter_version(self, tmp_path):
        path = tmp_path / "old.db"
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE snapshot_manifest (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                animal_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                source_revision TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                generated_by TEXT,
                is_read_only INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        for ddl in TABLES[1:]:
            conn.execute(ddl)
        conn.execute(
            "INSERT INTO snapshot_manifest (id, animal_id, schema_version, source_revision, generated_at)"
            " VALUES (1, ?, ?, ?, ?)",
            (str(uuid.uuid4()), SCHEMA_VERSION, "a" * 64, "2026-05-01T12:00:00+00:00"),
        )
        conn.commit()
        conn.close()
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), "--json", stdout=out)

        report = json.loads(out.getvalue())
        assert report["exporter_version"] is None
        assert report["schema_version"] == SCHEMA_VERSION


@pytest.mark.integration
class TestInspectCommandDriverFlag:
    def test_compare_drivers_ok(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), "--compare-drivers", stdout=out)

        output = out.getvalue()
        assert "Driver parity: OK" in output
        assert "Manifest parity: OK" in output
        assert "Row count parity: OK" in output
        assert "Row data parity: OK" in output
        assert "PRAGMA integrity_check (sqlite3): OK" in output

    def test_driver_sqlite_flag_matches_default(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        default_out = StringIO()
        sqlite_out = StringIO()

        call_command("inspect_animal_snapshot", str(path), stdout=default_out)
        call_command("inspect_animal_snapshot", str(path), "--driver", "sqlite", stdout=sqlite_out)

        assert default_out.getvalue() == sqlite_out.getvalue()

    def test_driver_libsql_flag(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)
        out = StringIO()

        call_command("inspect_animal_snapshot", str(path), "--driver", "libsql", stdout=out)

        output = out.getvalue()
        assert str(animal.id) in output
        assert f"Schema version: {SCHEMA_VERSION}" in output
        assert "Snapshot OK" in output
