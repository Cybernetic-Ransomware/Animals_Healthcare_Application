import pytest

from ahc.apps.animals.models import AnimalShare
from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote
from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
from ahc.apps.offline_snapshots.services import lifecycle
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
    request_snapshot_build,
    run_snapshot_build,
)

from ..helpers import _download_url, _manifest_url, _widget_url


@pytest.mark.integration
class TestManifestWithBuilding:
    def test_manifest_shows_building_without_current(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "building"
        assert manifest["snapshot_id"] == str(building.id)
        assert manifest["download_url"] is None
        assert manifest["building_snapshot_id"] == str(building.id)

    def test_manifest_keeps_ready_current_during_force_rebuild(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)
        building = request_snapshot_build(animal, profile, force=True)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == str(current.id)
        assert manifest["download_url"] == _download_url(animal, current.id)
        assert manifest["building_snapshot_id"] == str(building.id)

        run_snapshot_build(str(building.id))
        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == str(building.id)
        assert manifest["building_snapshot_id"] is None

    def test_manifest_reports_failed_when_nothing_better_exists(self, snapshot_animal, snapshot_dir, client, monkeypatch):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(lifecycle, "write_snapshot_file", _boom)
        run_snapshot_build(str(building.id))
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "failed"
        assert manifest["error_message"] == "boom"
        assert manifest["download_url"] is None
        assert manifest["building_snapshot_id"] is None

    def test_download_of_building_snapshot_is_404(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        building = request_snapshot_build(animal, profile)
        client.force_login(profile.user)

        response = client.get(_download_url(animal, building.id))

        assert response.status_code == 404


@pytest.mark.integration
class TestSnapshotFreshness:
    def test_fresh_ready_manifest_is_not_stale(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["is_stale"] is False
        assert manifest["latest_source_revision"] == manifest["source_revision"]
        assert manifest["can_rebuild"] is False

    def test_animal_field_change_marks_manifest_stale(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["is_stale"] is True
        assert manifest["latest_source_revision"] != manifest["source_revision"]
        assert manifest["can_rebuild"] is True

    def test_feeding_note_change_marks_manifest_stale(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        FeedingNote.objects.update(product_name="Other kibble")
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["is_stale"] is True

    def test_rebuild_restores_freshness(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        building = request_snapshot_build(animal, profile)
        run_snapshot_build(str(building.id))
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["snapshot_id"] == str(building.id)
        assert manifest["is_stale"] is False
        assert manifest["can_rebuild"] is False

    def test_stale_current_stays_downloadable_during_force_rebuild(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)
        animal.dietary_restrictions = "grain only, actually"
        animal.save()
        building = request_snapshot_build(animal, profile, force=True)
        client.force_login(profile.user)

        manifest = client.get(_manifest_url(animal)).json()

        assert manifest["status"] == "ready"
        assert manifest["snapshot_id"] == str(current.id)
        assert manifest["download_url"] == _download_url(animal, current.id)
        assert manifest["is_stale"] is True
        assert manifest["building_snapshot_id"] == str(building.id)
        assert manifest["can_rebuild"] is False

    def test_carer_freshness_tracks_only_visible_categories(
        self, snapshot_animal, second_user_profile, snapshot_dir, client
    ):
        animal, owner = snapshot_animal
        _, carer = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer, allow_diet=True)
        get_or_create_snapshot(animal, carer)
        get_or_create_snapshot(animal, owner)

        VaccinationNote.objects.update(vaccine_name="Rabies v2")

        client.force_login(carer.user)
        assert client.get(_manifest_url(animal)).json()["is_stale"] is False
        client.force_login(owner.user)
        assert client.get(_manifest_url(animal)).json()["is_stale"] is True

        FeedingNote.objects.update(product_name="Other kibble")
        client.force_login(carer.user)
        assert client.get(_manifest_url(animal)).json()["is_stale"] is True

    def test_widget_reports_stale_state_and_refresh_label(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        fresh = client.get(_widget_url(animal)).content.decode()
        assert "Ready, up to date" in fresh
        assert "Generate offline snapshot" in fresh

        animal.dietary_restrictions = "grain only, actually"
        animal.save()

        stale = client.get(_widget_url(animal)).content.decode()
        assert "Ready, but outdated" in stale
        assert "Refresh offline snapshot" in stale
