import pytest

from ahc.apps.offline_snapshots import tasks as snapshot_tasks
from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.lifecycle import (
    get_or_create_snapshot,
)

from ..helpers import _download_url, _rebuild_url, _widget_url


@pytest.fixture
def captured_enqueues(monkeypatch):
    """Record build_snapshot_task.apply_async calls instead of talking to the broker."""
    calls = []
    monkeypatch.setattr(snapshot_tasks.build_snapshot_task, "apply_async", lambda **kwargs: calls.append(kwargs))
    return calls


@pytest.mark.integration
class TestAsyncRebuildRequest:
    def test_post_without_current_returns_202_and_enqueues(
        self, snapshot_animal, snapshot_dir, client, captured_enqueues, django_capture_on_commit_callbacks
    ):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(_rebuild_url(animal))

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "building"
        assert body["download_url"] is None
        snapshot = AnimalSnapshot.objects.get(id=body["snapshot_id"])
        assert snapshot.status == SnapshotStatus.BUILDING
        assert snapshot.task_id
        assert captured_enqueues == [{"args": [str(snapshot.id)], "task_id": snapshot.task_id}]

    def test_fresh_current_returns_200_without_enqueue(
        self, snapshot_animal, snapshot_dir, client, captured_enqueues, django_capture_on_commit_callbacks
    ):
        animal, profile = snapshot_animal
        current = get_or_create_snapshot(animal, profile)
        client.force_login(profile.user)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(_rebuild_url(animal))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["snapshot_id"] == str(current.id)
        assert body["download_url"] == _download_url(animal, current.id)
        assert captured_enqueues == []

    def test_second_post_during_building_is_deduped(
        self, snapshot_animal, snapshot_dir, client, captured_enqueues, django_capture_on_commit_callbacks
    ):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        with django_capture_on_commit_callbacks(execute=True):
            first = client.post(_rebuild_url(animal))
        with django_capture_on_commit_callbacks(execute=True):
            second = client.post(_rebuild_url(animal), {"force": "1"})

        assert first.status_code == 202
        assert second.status_code == 202
        assert second.json()["snapshot_id"] == first.json()["snapshot_id"]
        assert AnimalSnapshot.objects.filter(status=SnapshotStatus.BUILDING).count() == 1
        assert len(captured_enqueues) == 1

    def test_stranger_post_creates_no_row(self, snapshot_animal, second_user_profile, snapshot_dir, client):
        animal, _ = snapshot_animal
        stranger_user, _ = second_user_profile
        client.force_login(stranger_user)

        response = client.post(_rebuild_url(animal))

        assert response.status_code == 403
        assert AnimalSnapshot.objects.count() == 0

    def test_rebuild_with_hx_header_returns_widget_html(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.post(_rebuild_url(animal), headers={"HX-Request": "true"})

        assert response.status_code == 200
        content = response.content.decode()
        assert "offline-snapshot-widget" in content
        assert "Building" in content

    def test_widget_shows_missing_state(self, snapshot_animal, snapshot_dir, client):
        animal, profile = snapshot_animal
        client.force_login(profile.user)

        response = client.get(_widget_url(animal))

        assert response.status_code == 200
        assert "Missing" in response.content.decode()
