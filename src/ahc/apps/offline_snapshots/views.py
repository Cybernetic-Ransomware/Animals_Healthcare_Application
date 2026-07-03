"""Manifest, rebuild, download and widget endpoints for offline snapshots (ADR-12, stages 2-4).

Plain JsonResponse views — ADR-07 (API framework) is still pending, so no DRF.
Snapshot files live in private storage with no public URL; the download view
is the only way to fetch them. Rebuild is asynchronous: POST enqueues a Celery
build and answers 202, the manifest (or the htmx widget) reports progress.
A READY manifest also reports freshness: the stored source_revision is
compared against the live profile-scoped payload revision on every read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import user_can_view_animal
from ahc.apps.offline_snapshots.models import AnimalSnapshot, SnapshotStatus
from ahc.apps.offline_snapshots.services.lifecycle import (
    active_building_snapshot_for,
    current_snapshot_for,
    request_snapshot_build,
    snapshot_freshness_for,
)
from ahc.apps.offline_snapshots.services.storage import snapshot_path

if TYPE_CHECKING:
    from ahc.apps.users.models import Profile
    from ahc.types import AuthenticatedRequest


def _forbidden() -> JsonResponse:
    return JsonResponse({"status": "forbidden"}, status=403)


def _missing(animal: Animal) -> JsonResponse:
    return JsonResponse({"animal_id": str(animal.id), "status": "missing", "can_generate": True})


def _download_url(animal: Animal, snapshot: AnimalSnapshot) -> str | None:
    if snapshot.status != SnapshotStatus.READY:
        return None
    return reverse("offline_snapshot_download", kwargs={"pk": animal.pk, "snapshot_id": snapshot.id})


def _snapshot_payload(animal: Animal, snapshot: AnimalSnapshot) -> dict:
    payload = {
        "animal_id": str(animal.id),
        "snapshot_id": str(snapshot.id),
        "status": snapshot.status,
        "schema_version": snapshot.schema_version,
        "source_revision": snapshot.source_revision,
        "generated_at": snapshot.generated_at.isoformat(),
        "file_size_bytes": snapshot.file_size_bytes,
        "download_url": _download_url(animal, snapshot),
    }
    if snapshot.status == SnapshotStatus.FAILED:
        payload["error_message"] = snapshot.error_message
    return payload


def _snapshot_state(
    animal: Animal, profile: Profile
) -> tuple[AnimalSnapshot | None, AnimalSnapshot | None, AnimalSnapshot | None]:
    """Resolve (current READY, active BUILDING, latest FAILED) for the pair.

    A current row whose file vanished (e.g. redeploy without a volume) is
    treated as absent, and FAILED is only surfaced when there is nothing
    better to show.
    """
    current = current_snapshot_for(animal, profile)
    if current is not None and not snapshot_path(current.storage_key).exists():
        current = None
    building = active_building_snapshot_for(animal, profile)
    failed = None
    if current is None and building is None:
        failed = (
            AnimalSnapshot.objects.filter(animal=animal, generated_for=profile, status=SnapshotStatus.FAILED)
            .order_by("-generated_at")
            .first()
        )
    return current, building, failed


def _manifest_payload(animal: Animal, profile: Profile, current, building, failed) -> dict | None:
    """Full manifest dict for the pair, or None when there is nothing to report.

    Freshness keys are present only for a READY current artifact; can_rebuild
    is offered when the data changed and no build is already running.
    """
    snapshot = current or building or failed
    if snapshot is None:
        return None
    payload = _snapshot_payload(animal, snapshot)
    payload["building_snapshot_id"] = str(building.id) if building else None
    freshness = snapshot_freshness_for(animal, profile, current)
    if freshness is not None:
        payload.update(freshness)
        payload["can_rebuild"] = freshness["is_stale"] and building is None
    return payload


def _render_widget(request, animal: Animal, profile: Profile):
    current, building, failed = _snapshot_state(animal, profile)
    freshness = snapshot_freshness_for(animal, profile, current)
    context = {
        "animal": animal,
        "current": current,
        "building": building,
        "failed": failed,
        "is_stale": freshness["is_stale"] if freshness else False,
        "download_url": _download_url(animal, current) if current else None,
    }
    return render(request, "offline_snapshots/_snapshot_widget.html", context)


class SnapshotManifestView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

    def get(self, request, *args, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        profile = request.user.profile
        if not user_can_view_animal(profile, animal):
            return _forbidden()
        payload = _manifest_payload(animal, profile, *_snapshot_state(animal, profile))
        if payload is None:
            return _missing(animal)
        return JsonResponse(payload)


class SnapshotRebuildView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

    def post(self, request, *args, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        profile = request.user.profile
        force = request.POST.get("force") in {"1", "true", "on"}
        try:
            request_snapshot_build(animal, profile, force=force)
        except PermissionDenied:
            return _forbidden()
        if request.headers.get("HX-Request"):
            return _render_widget(request, animal, profile)
        # Manifest-shaped response: during a force rebuild the READY current
        # stays the payload subject while 202 signals the running build.
        current, building, failed = _snapshot_state(animal, profile)
        payload = _manifest_payload(animal, profile, current, building, failed)
        if payload is None:
            return _missing(animal)
        status_code = 202 if building is not None else 200
        return JsonResponse(payload, status=status_code)


class SnapshotWidgetView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

    def get(self, request, *args, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        profile = request.user.profile
        if not user_can_view_animal(profile, animal):
            return _forbidden()
        return _render_widget(request, animal, profile)


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
