"""Shared helpers for the offline_snapshots tests.

Snapshot files are read back with the stdlib sqlite3 module on purpose:
this proves the artifact produced via the Turso driver is a standard,
portable SQLite database.
"""

import sqlite3


def _query(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _saved_response_db(response, tmp_path):
    """Write a streamed download response to disk so it can be queried with sqlite3."""
    target = tmp_path / "downloaded.db"
    target.write_bytes(b"".join(response.streaming_content))
    return target


def _manifest_url(animal):
    return f"/pet/{animal.id}/offline-snapshot/"


def _rebuild_url(animal):
    return f"/pet/{animal.id}/offline-snapshot/rebuild/"


def _widget_url(animal):
    return f"/pet/{animal.id}/offline-snapshot/widget/"


def _download_url(animal, snapshot_id):
    return f"/pet/{animal.id}/offline-snapshot/{snapshot_id}/download/"
