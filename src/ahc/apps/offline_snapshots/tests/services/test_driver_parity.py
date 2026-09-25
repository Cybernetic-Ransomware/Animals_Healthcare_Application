import json
import os
import sqlite3
import sys
from decimal import Decimal

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord, BiometricWeightRecords
from ahc.apps.offline_snapshots.services.driver_parity import (
    compare_drivers,
    read_snapshot_libsql,
    read_snapshot_sqlite3,
)
from ahc.apps.offline_snapshots.services.exporter import build_export_plan, export_animal_snapshot, write_snapshot_file


@pytest.fixture
def edge_case_snapshot(db, user_profile, tmp_path):
    """Snapshot with edge-case data: Polish characters, emoji, newlines, Decimal weight, NULL fields.

    Column indices used by TestEdgeCaseRoundTrip come from schema.py DDL order:
      animal_snapshot:         [1]=full_name  [2]=species  [3]=breed
      medical_record_snapshot: [8]=short_description  [9]=full_description  [11]=tags_json
      biometric_snapshot:      [4]=weight
    """
    _, profile = user_profile
    animal = Animal.objects.create(full_name="Żółć Łódź", owner=profile)

    visit = MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description="Check-up \U0001f415",
        full_description="Line one\nLine two\nLine three",
        type_of_event="medical_visit",
    )
    visit.note_tags.add("żagiel", "łódź")

    bio_shell = MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description="Weighing",
        type_of_event="biometric_record",
    )
    weight_rec = BiometricWeightRecords.objects.create(weight=Decimal("12.375"))
    BiometricRecord.objects.create(animal=animal, related_note=bio_shell, weight_biometric_record=weight_rec)

    path = export_animal_snapshot(animal, profile, tmp_path)
    return path, animal


@pytest.mark.integration
class TestDriverParity:
    def test_manifest_parity(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)

        sqlite_read = read_snapshot_sqlite3(path)
        libsql_read = read_snapshot_libsql(path)

        assert sqlite_read.manifest == libsql_read.manifest

    def test_row_count_parity(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)

        sqlite_read = read_snapshot_sqlite3(path)
        libsql_read = read_snapshot_libsql(path)

        assert sqlite_read.row_counts == libsql_read.row_counts

    def test_row_data_parity(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)

        sqlite_read = read_snapshot_sqlite3(path, fetch_rows=True)
        libsql_read = read_snapshot_libsql(path, fetch_rows=True)

        assert sqlite_read.table_rows == libsql_read.table_rows


@pytest.mark.integration
class TestEdgeCaseRoundTrip:
    def test_unicode_round_trip(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path, fetch_rows=True)
            (animal_row,) = result.table_rows["animal_snapshot"]
            assert "Żółć Łódź" in animal_row

    def test_emoji_round_trip(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path, fetch_rows=True)
            short_descs = [row[8] for row in result.table_rows["medical_record_snapshot"]]
            assert any("\U0001f415" in (desc or "") for desc in short_descs)

    def test_newline_in_text_round_trip(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path, fetch_rows=True)
            full_descs = [row[9] for row in result.table_rows["medical_record_snapshot"]]
            assert any("\n" in (desc or "") for desc in full_descs)

    def test_decimal_as_text_round_trip(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path, fetch_rows=True)
            weights = [row[4] for row in result.table_rows["biometric_snapshot"]]
            assert "12.375" in weights

    def test_json_tags_round_trip(self, edge_case_snapshot):
        path, _ = edge_case_snapshot
        # json.dumps uses ensure_ascii=True by default, matching the exporter.
        # sorted(["żagiel", "łódź"]) → ["łódź", "żagiel"] (ł U+0142 < ż U+017C).
        expected_tags = json.dumps(["łódź", "żagiel"])

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path, fetch_rows=True)
            tags_cells = [row[11] for row in result.table_rows["medical_record_snapshot"]]
            assert expected_tags in tags_cells

    def test_null_fields(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path, fetch_rows=True)
            (animal_row,) = result.table_rows["animal_snapshot"]
            assert animal_row[2] is None
            assert animal_row[3] is None

    def test_iso_date_format(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        for read_fn in (read_snapshot_sqlite3, read_snapshot_libsql):
            result = read_fn(path)
            generated_at = result.manifest["generated_at"]
            assert isinstance(generated_at, str)
            assert "T" in generated_at

    def test_row_data_parity_edge_cases(self, edge_case_snapshot):
        path, _ = edge_case_snapshot

        sqlite_read = read_snapshot_sqlite3(path, fetch_rows=True)
        libsql_read = read_snapshot_libsql(path, fetch_rows=True)

        assert sqlite_read.table_rows == libsql_read.table_rows


@pytest.mark.integration
class TestPragmaIntegrity:
    def test_integrity_check_passes(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)

        report = compare_drivers(path)

        assert report.integrity_ok is True


@pytest.mark.integration
class TestAtomicReplace:
    def test_atomic_replace_parity(self, snapshot_animal, tmp_path):
        """After os.replace, both drivers read the same new revision from the rebuilt file."""
        animal, profile = snapshot_animal
        path = export_animal_snapshot(animal, profile, tmp_path)

        animal.dietary_restrictions = "only fish"
        animal.save()
        export_animal_snapshot(animal, profile, tmp_path, force=True)

        sqlite_read = read_snapshot_sqlite3(path)
        libsql_read = read_snapshot_libsql(path)
        assert sqlite_read.manifest["source_revision"] == libsql_read.manifest["source_revision"]
        report = compare_drivers(path)
        assert report.ok


@pytest.mark.integration
class TestAtomicReplaceReadWhileOpen:
    """Document platform-specific behaviour of os.replace() against an open sqlite3 connection.

    On POSIX, os.replace() swaps the directory entry atomically; the old file descriptor
    keeps pointing at the old inode, so the reader continues without error.

    On Windows, os.replace() raises PermissionError when the destination file has an open
    connection — even a read-only one. Consumers must close their connection before the
    lifecycle triggers a rebuild, or the rebuild will fail at the os.replace() step.
    """

    def test_atomic_replace_behaviour_with_open_connection(self, snapshot_animal, tmp_path):
        animal, profile = snapshot_animal
        plan = build_export_plan(animal, profile)
        snap_path = tmp_path / "snap.db"
        write_snapshot_file(animal, profile, plan, snap_path)

        conn = sqlite3.connect(f"file:{snap_path.as_posix()}?mode=ro", uri=True)
        conn.execute("SELECT source_revision FROM snapshot_manifest").fetchone()

        replacement = tmp_path / "snap_new.db"
        write_snapshot_file(animal, profile, plan, replacement)

        if sys.platform == "win32":
            # Windows does not allow replacing a file that has an open handle,
            # even when opened read-only.
            with pytest.raises(PermissionError):
                os.replace(replacement, snap_path)
            conn.close()
        else:
            os.replace(replacement, snap_path)
            # POSIX: old file descriptor stays valid; replace is invisible to the reader.
            conn.execute("SELECT source_revision FROM snapshot_manifest").fetchone()
            conn.close()
            new_conn = sqlite3.connect(f"file:{snap_path.as_posix()}?mode=ro", uri=True)
            new_conn.execute("SELECT source_revision FROM snapshot_manifest").fetchone()
            new_conn.close()
