"""Consumer-side reader for exported animal snapshot files (ADR-12).

Reads with the stdlib sqlite3 module on purpose: any standard SQLite client
must be able to consume a snapshot, so the inspector must not depend on the
Turso driver that wrote the file.
"""

import sqlite3
from pathlib import Path

from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION, TABLE_NAMES

MANIFEST_TABLE = "snapshot_manifest"


class SnapshotInspectionError(Exception):
    """Raised when a snapshot file is missing, unreadable, or incompatible."""


def inspect_snapshot(path: Path) -> dict:
    """Validate a snapshot file and return its manifest plus per-table row counts."""
    if not path.is_file():
        raise SnapshotInspectionError(f"File not found: {path}")

    # mode=ro keeps the read-only contract and prevents sqlite3 from creating
    # an empty database at a mistyped path.
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        manifest = _read_manifest(conn, path)
        _validate_schema_version(manifest, path)
        row_counts = _count_rows(conn, path)
    finally:
        conn.close()

    return {
        "path": str(path),
        "animal_id": manifest["animal_id"],
        "schema_version": manifest["schema_version"],
        "exporter_version": manifest["exporter_version"],
        "source_revision": manifest["source_revision"],
        "generated_at": manifest["generated_at"],
        "generated_by": manifest["generated_by"],
        "is_read_only": bool(manifest["is_read_only"]),
        "row_counts": row_counts,
    }


def _read_manifest(conn: sqlite3.Connection, path: Path) -> sqlite3.Row:
    try:
        row = conn.execute("SELECT * FROM snapshot_manifest WHERE id = 1").fetchone()
    except sqlite3.DatabaseError as exc:
        raise SnapshotInspectionError(f"Not a valid SQLite snapshot: {path} ({exc})") from exc
    if row is None:
        raise SnapshotInspectionError(f"Not a valid SQLite snapshot: {path} (empty {MANIFEST_TABLE})")
    return row


def _validate_schema_version(manifest: sqlite3.Row, path: Path) -> None:
    found = manifest["schema_version"]
    if found != SCHEMA_VERSION:
        raise SnapshotInspectionError(f"Unsupported schema_version {found} in {path}; this build supports {SCHEMA_VERSION}")


def _count_rows(conn: sqlite3.Connection, path: Path) -> dict[str, int]:
    counts = {}
    for table in TABLE_NAMES:
        if table == MANIFEST_TABLE:
            continue
        try:
            # Table names come from the TABLE_NAMES constant, not user input.
            (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # nosec B608
        except sqlite3.DatabaseError as exc:
            raise SnapshotInspectionError(f"Not a valid SQLite snapshot: {path} (missing table {table})") from exc
        counts[table] = count
    return counts
