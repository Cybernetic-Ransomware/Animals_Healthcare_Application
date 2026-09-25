from pathlib import Path

import pytest
from django.conf import settings as django_settings

from ahc.apps.offline_snapshots.services.storage import snapshot_path


@pytest.mark.unit
class TestSnapshotStorage:
    def test_traversal_key_is_rejected(self):
        with pytest.raises(ValueError, match="Invalid snapshot storage key"):
            snapshot_path("../../etc/passwd")

    def test_snapshot_root_is_not_under_media_root(self):
        snapshot_root = Path(django_settings.OFFLINE_SNAPSHOT_ROOT).resolve()
        media_root = Path(django_settings.MEDIA_ROOT).resolve()
        assert not snapshot_root.is_relative_to(media_root)
