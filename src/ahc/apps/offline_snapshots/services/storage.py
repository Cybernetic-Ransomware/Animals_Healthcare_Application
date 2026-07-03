"""Private filesystem storage for offline snapshot files (see ADR-12, stage 2).

Snapshot .db files contain medical data and must never live under MEDIA_ROOT,
which is served without authentication. Files are reachable only through the
permission-checked download view; there is no public URL for a snapshot.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings


def snapshot_path(storage_key: str) -> Path:
    """Resolve a storage key to an absolute path inside OFFLINE_SNAPSHOT_ROOT.

    Raises ValueError when the key would escape the snapshot root.
    """
    root = Path(settings.OFFLINE_SNAPSHOT_ROOT).resolve()
    path = (root / storage_key).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid snapshot storage key.")
    return path


def build_snapshot_storage_key(snapshot_id) -> str:
    return f"{snapshot_id}.db"
