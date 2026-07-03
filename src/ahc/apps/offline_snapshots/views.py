"""Manifest, rebuild and download endpoints for offline snapshots (ADR-12, stage 2).

Plain JsonResponse views — ADR-07 (API framework) is still pending, so no DRF.
Snapshot files live in private storage with no public URL; the download view
is the only way to fetch them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import user_can_view_animal
from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.lifecycle import current_snapshot_for, get_or_create_snapshot
from ahc.apps.offline_snapshots.services.storage import snapshot_path

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


def _forbidden() -> JsonResponse:
    return JsonResponse({"status": "forbidden"}, status=403)


def _download_url(animal: Animal, snapshot: AnimalSnapshot) -> str | None:
    if snapshot.status != SnapshotStatus.READY:
        return None
    return reverse("offline_snapshot_download", kwargs={"pk": animal.pk, "snapshot_id": snapshot.id})


def _snapshot_payload(animal: Animal, snapshot: AnimalSnapshot) -> dict:
    return {
        "animal_id": str(animal.id),
        "snapshot_id": str(snapshot.id),
        "status": snapshot.status,
        "schema_version": snapshot.schema_version,
        "source_revision": snapshot.source_revision,
        "generated_at": snapshot.generated_at.isoformat(),
        "file_size_bytes": snapshot.file_size_bytes,
        "download_url": _download_url(animal, snapshot),
    }


class SnapshotManifestView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

    def get(self, request, *args, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        profile = request.user.profile
        if not user_can_view_animal(profile, animal):
            return _forbidden()
        snapshot = current_snapshot_for(animal, profile)
        if snapshot is None:
            return JsonResponse({"animal_id": str(animal.id), "status": "missing", "can_generate": True})
        return JsonResponse(_snapshot_payload(animal, snapshot))


class SnapshotRebuildView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

    def post(self, request, *args, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        force = request.POST.get("force") in {"1", "true", "on"}
        try:
            snapshot = get_or_create_snapshot(animal, request.user.profile, force=force)
        except PermissionDenied:
            return _forbidden()
        payload = {
            "status": snapshot.status,
            "snapshot_id": str(snapshot.id),
            "source_revision": snapshot.source_revision,
            "download_url": _download_url(animal, snapshot),
        }
        if snapshot.status == SnapshotStatus.FAILED:
            payload["error_message"] = snapshot.error_message
        return JsonResponse(payload)


class SnapshotDownloadView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

    def get(self, request, *args, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        profile = request.user.profile
        if not user_can_view_animal(profile, animal):
            return _forbidden()
        # Filtering by generated_for makes another profile's artifact (e.g. the
        # owner's full snapshot requested by a carer) unaddressable by design.
        snapshot = AnimalSnapshot.objects.filter(
            id=self.kwargs["snapshot_id"], animal=animal, generated_for=profile
        ).first()
        if snapshot is None or snapshot.status != SnapshotStatus.READY:
            raise Http404
        path = snapshot_path(snapshot.storage_key)
        if not path.exists():
            raise Http404
        return FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename=f"animal_{animal.id}_snapshot.db",
            content_type="application/vnd.sqlite3",
        )
