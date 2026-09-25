import pytest

from ahc.apps.animals.models import AnimalShare
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    run_snapshot_build,
)
from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION
from ahc.apps.offline_snapshots.services.storage import snapshot_path

from ..helpers import _query, _saved_response_db


@pytest.mark.integration
class TestSnapshotEndpoints:
    @staticmethod
    def _manifest_url(animal):
        return f"/pet/{animal.id}/offline-snapshot/"

    @staticmethod
    def _rebuild_url(animal):
        return f"/pet/{animal.id}/offline-snapshot/rebuild/"

    @staticmethod
    def _download_url(animal, snapshot_id):
        return f"/pet/{animal.id}/offline-snapshot/{snapshot_id}/download/"

    def test_manifest_missing_reports_can_generate(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.get(self._manifest_url(animal))

        assert response.status_code == 200
        assert response.json() == {"animal_id": str(animal.id), "status": "missing", "can_generate": True}

    def test_rebuild_then_manifest_round_trip(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        rebuild_response = client.post(self._rebuild_url(animal))
        rebuild = rebuild_response.json()
        run_snapshot_build(rebuild["snapshot_id"])
        manifest = client.get(self._manifest_url(animal)).json()

        assert rebuild_response.status_code == 202
        assert rebuild["status"] == "building"
        assert rebuild["download_url"] is None
        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == rebuild["snapshot_id"]
        assert manifest["source_revision"] == rebuild["source_revision"]
        assert manifest["schema_version"] == SCHEMA_VERSION
        assert manifest["file_size_bytes"] > 0
        assert manifest["building_snapshot_id"] is None
        assert manifest["download_url"] == self._download_url(animal, rebuild["snapshot_id"])

    def test_stranger_gets_403_on_all_endpoints(self, snapshot_animal, second_user_profile, snapshot_dir, client):
        animal, owner = snapshot_animal
        snapshot = get_or_create_snapshot(animal, owner)
        stranger_user, _ = second_user_profile
        client.force_login(stranger_user)

        assert client.get(self._manifest_url(animal)).status_code == 403
        assert client.post(self._rebuild_url(animal)).status_code == 403
        assert client.get(self._download_url(animal, snapshot.id)).status_code == 403

    def test_carer_downloads_own_filtered_file(self, snapshot_animal, second_user_profile, snapshot_dir, client, tmp_path):
        animal, _ = snapshot_animal
        carer_user, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        snapshot = get_or_create_snapshot(animal, carer)
        client.force_login(carer_user)

        response = client.get(self._download_url(animal, snapshot.id))

        assert response.status_code == 200
        downloaded = _saved_response_db(response, tmp_path)
        (manifest,) = _query(downloaded, "SELECT source_revision FROM snapshot_manifest")
        assert manifest["source_revision"] == snapshot.source_revision
        records = _query(downloaded, "SELECT type_of_event FROM medical_record_snapshot")
        assert {r["type_of_event"] for r in records} == {"diet_note"}

    def test_carer_cannot_download_owners_snapshot(self, snapshot_animal, second_user_profile, snapshot_dir, client):
        animal, owner = snapshot_animal
        owner_snapshot = get_or_create_snapshot(animal, owner)
        carer_user, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        client.force_login(carer_user)

        response = client.get(self._download_url(animal, owner_snapshot.id))

        assert response.status_code == 404

    def test_download_headers(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        response = client.get(self._download_url(animal, snapshot.id))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.sqlite3"
        assert "attachment" in response["Content-Disposition"]
        assert f"animal_{animal.id}_snapshot.db" in response["Content-Disposition"]

    def test_manifest_reflects_new_revision_after_change(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)
        first = client.post(self._rebuild_url(animal)).json()
        run_snapshot_build(first["snapshot_id"])

        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        second = client.post(self._rebuild_url(animal)).json()
        run_snapshot_build(second["building_snapshot_id"])
        manifest = client.get(self._manifest_url(animal)).json()

        # The rebuild response keeps the stale READY current as its subject;
        # the enqueued replacement is addressed via building_snapshot_id.
        assert second["snapshot_id"] == first["snapshot_id"]
        assert second["is_stale"] is True
        assert second["latest_source_revision"] != first["source_revision"]
        assert manifest["source_revision"] == second["latest_source_revision"]
        assert manifest["is_stale"] is False
        assert manifest["download_url"] == self._download_url(animal, second["building_snapshot_id"])

    def test_manifest_reports_missing_when_file_deleted(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        snapshot = get_or_create_snapshot(animal, profile)
        snapshot_path(snapshot.storage_key).unlink()
        client.force_login(profile.user)

        response = client.get(self._manifest_url(animal))

        assert response.status_code == 200
        assert response.json() == {"animal_id": str(animal.id), "status": "missing", "can_generate": True}

    def test_anonymous_is_redirected_to_login(self, snapshot_animal, snapshot_dir, client):
        animal, _ = snapshot_animal

        response = client.get(self._manifest_url(animal))

        assert response.status_code == 302
        assert "login" in response["Location"]
