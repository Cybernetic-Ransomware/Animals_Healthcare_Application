import pytest

from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
)
from ahc.apps.offline_snapshots.services.schema import EXPORTER_VERSION, SCHEMA_VERSION
from ahc.apps.offline_snapshots.services.storage import snapshot_path

from ..helpers import _query


@pytest.mark.integration
class TestSchemaVersioning:
    def test_model_row_and_manifest_carry_same_schema_version(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)

        (manifest,) = _query(snapshot_path(snapshot.storage_key), "SELECT * FROM snapshot_manifest")

        assert manifest["schema_version"] == snapshot.schema_version == SCHEMA_VERSION

    def test_manifest_carries_exporter_version(self, snapshot_animal, snapshot_dir):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)

        (manifest,) = _query(snapshot_path(snapshot.storage_key), "SELECT exporter_version FROM snapshot_manifest")

        assert manifest["exporter_version"] == EXPORTER_VERSION


@pytest.mark.unit
def test_schema_version_bump_is_deliberate():
    # Bumping SCHEMA_VERSION is a breaking change for every snapshot reader.
    # Re-read the compatibility contract in ADR-12 (stage 5) before touching
    # this assertion: additive changes must NOT bump the version.
    assert SCHEMA_VERSION == 1
