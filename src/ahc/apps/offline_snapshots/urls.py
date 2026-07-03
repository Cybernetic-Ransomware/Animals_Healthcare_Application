from django.urls import path

from ahc.apps.offline_snapshots import views

urlpatterns = [
    path("", views.SnapshotManifestView.as_view(), name="offline_snapshot_manifest"),
    path("rebuild/", views.SnapshotRebuildView.as_view(), name="offline_snapshot_rebuild"),
    path("widget/", views.SnapshotWidgetView.as_view(), name="offline_snapshot_widget"),
    path("<uuid:snapshot_id>/download/", views.SnapshotDownloadView.as_view(), name="offline_snapshot_download"),
]
