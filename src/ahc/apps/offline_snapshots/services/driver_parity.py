"""Cross-driver parity reader for offline snapshot files (ADR-12).

Both drivers read the same .db file and results are compared to verify that
the Turso/libSQL write path and the stdlib sqlite3 read path see identical
data — no silent type coercions, encoding differences, or NULL/empty mismatches.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import turso

from ahc.apps.offline_snapshots.services.inspector import MANIFEST_TABLE
from ahc.apps.offline_snapshots.services.schema import TABLE_NAMES

_DATA_TABLES: tuple[str, ...] = tuple(t for t in TABLE_NAMES if t != MANIFEST_TABLE)


@dataclass
class SnapshotRead:
    """Raw read result from a single driver."""

    manifest: dict
    row_counts: dict[str, int]
    table_rows: dict[str, list[tuple]] = field(default_factory=dict)


@dataclass
class ParityReport:
    """Comparison result between sqlite3 and libSQL over the same snapshot file."""

    ok: bool
    sqlite_read: SnapshotRead
    libsql_read: SnapshotRead
    manifest_diff: dict | None
    row_count_diff: dict | None
    row_data_diff: dict | None
    integrity_ok: bool


def read_snapshot_sqlite3(path: Path, *, fetch_rows: bool = False) -> SnapshotRead:
    """Read a snapshot file through the stdlib sqlite3 driver.

    row_factory is intentionally NOT set so that fetchall() returns plain tuples,
    enabling direct == comparison with the libSQL driver's output.
    """
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        cur = conn.execute(f"SELECT * FROM {MANIFEST_TABLE} WHERE id = 1")  # nosec B608
        assert cur.description is not None
        col_names = [d[0] for d in cur.description]
        manifest = dict(zip(col_names, cur.fetchone(), strict=True))

        row_counts: dict[str, int] = {}
        table_rows: dict[str, list[tuple]] = {}
        for table in _DATA_TABLES:
            (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # nosec B608
            row_counts[table] = count
            if fetch_rows:
                table_rows[table] = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()  # nosec B608
    finally:
        conn.close()
    return SnapshotRead(manifest=manifest, row_counts=row_counts, table_rows=table_rows)


def read_snapshot_libsql(path: Path, *, fetch_rows: bool = False) -> SnapshotRead:
    """Read a snapshot file through the Turso/libSQL driver.

    turso.connect() only accepts a string path; there is no read-only URI mode.
    Only SELECT statements are issued so the file is not modified in practice.
    """
    conn = turso.connect(str(path))
    try:
        cur = conn.execute(f"SELECT * FROM {MANIFEST_TABLE} WHERE id = 1")  # nosec B608
        assert cur.description is not None
        col_names = [d[0] for d in cur.description]
        manifest = dict(zip(col_names, cur.fetchone(), strict=True))

        row_counts: dict[str, int] = {}
        table_rows: dict[str, list[tuple]] = {}
        for table in _DATA_TABLES:
            (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # nosec B608
            row_counts[table] = count
            if fetch_rows:
                table_rows[table] = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()  # nosec B608
    finally:
        conn.close()
    return SnapshotRead(manifest=manifest, row_counts=row_counts, table_rows=table_rows)


def _diff_manifests(a: dict, b: dict) -> dict | None:
    diff = {k: {"sqlite3": a.get(k), "libsql": b.get(k)} for k in set(a) | set(b) if a.get(k) != b.get(k)}
    return diff or None


def _diff_row_counts(a: dict[str, int], b: dict[str, int]) -> dict | None:
    diff = {t: {"sqlite3": a.get(t), "libsql": b.get(t)} for t in _DATA_TABLES if a.get(t) != b.get(t)}
    return diff or None


def _diff_table_rows(a: dict[str, list[tuple]], b: dict[str, list[tuple]]) -> dict | None:
    diff = {
        table: {"sqlite3_rows": len(a.get(table, [])), "libsql_rows": len(b.get(table, []))}
        for table in _DATA_TABLES
        if a.get(table) != b.get(table)
    }
    return diff or None


def _check_integrity(path: Path) -> bool:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        return rows == [("ok",)]
    finally:
        conn.close()


def compare_drivers(path: Path) -> ParityReport:
    """Read the snapshot through both drivers and return a structured parity report."""
    sqlite_read = read_snapshot_sqlite3(path, fetch_rows=True)
    libsql_read = read_snapshot_libsql(path, fetch_rows=True)
    manifest_diff = _diff_manifests(sqlite_read.manifest, libsql_read.manifest)
    row_count_diff = _diff_row_counts(sqlite_read.row_counts, libsql_read.row_counts)
    row_data_diff = _diff_table_rows(sqlite_read.table_rows, libsql_read.table_rows)
    integrity_ok = _check_integrity(path)
    ok = manifest_diff is None and row_count_diff is None and row_data_diff is None and integrity_ok
    return ParityReport(
        ok=ok,
        sqlite_read=sqlite_read,
        libsql_read=libsql_read,
        manifest_diff=manifest_diff,
        row_count_diff=row_count_diff,
        row_data_diff=row_data_diff,
        integrity_ok=integrity_ok,
    )
