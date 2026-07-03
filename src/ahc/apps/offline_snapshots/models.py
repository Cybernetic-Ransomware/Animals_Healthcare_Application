import uuid

from django.db import models
from django.db.models import Q

from ahc.apps.animals.models import Animal
from ahc.apps.users.models import Profile


class SnapshotStatus(models.TextChoices):
    READY = "ready", "Ready"
    BUILDING = "building", "Building"
    FAILED = "failed", "Failed"


class SnapshotStorageBackend(models.TextChoices):
    LOCAL_PRIVATE = "local_private", "Local private filesystem"


class AnimalSnapshot(models.Model):
    """Immutable artifact row for one snapshot build attempt (see ADR-12, stage 2).

    Each build creates a new row; rows are never rewritten to point at a
    different file. is_current marks the latest successful build for the
    (animal, generated_for) pair and moves only after the new file exists
    on disk. FAILED rows are never current, so a failed rebuild leaves the
    previous artifact untouched and downloadable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="offline_snapshots")
    generated_for = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="offline_snapshots")
    schema_version = models.PositiveIntegerField()
    source_revision = models.CharField(max_length=64)
    allowed_categories_json = models.JSONField(default=list, blank=True)
    storage_backend = models.CharField(
        max_length=32, choices=SnapshotStorageBackend.choices, default=SnapshotStorageBackend.LOCAL_PRIVATE
    )
    storage_key = models.CharField(max_length=500, unique=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=10, choices=SnapshotStatus.choices, default=SnapshotStatus.BUILDING)
    error_message = models.CharField(max_length=2500, default=None, blank=True, null=True)
    is_current = models.BooleanField(default=False)
    task_id = models.CharField(max_length=255, blank=True, default="")
    build_started_at = models.DateTimeField(default=None, blank=True, null=True)
    build_finished_at = models.DateTimeField(default=None, blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    superseded_at = models.DateTimeField(default=None, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["animal", "generated_for"],
                condition=Q(is_current=True),
                name="uniq_current_snapshot_per_animal_profile",
            )
        ]

    def __str__(self):
        return f"Snapshot {self.id} ({self.status}) of {self.animal_id} for {self.generated_for_id}"  # type: ignore


class DownloadOutcome(models.TextChoices):
    SUCCESS = "success", "Success"
    FORBIDDEN = "forbidden", "Forbidden"
    NOT_FOUND = "not_found", "Not found"


class SnapshotDownloadLog(models.Model):
    """Append-only audit row for one snapshot download attempt (ADR-12, stage 5).

    Denied attempts (403/404) are recorded too — snapshots carry medical data,
    so who tried to fetch what matters as much as who succeeded. The snapshot
    FK is SET_NULL: pruning deletes artifact rows after a few days and the
    audit entry must outlive them; a 404 attempt never had a row to begin with.
    """

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="snapshot_download_logs")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="snapshot_download_logs")
    snapshot = models.ForeignKey(
        AnimalSnapshot, on_delete=models.SET_NULL, default=None, blank=True, null=True, related_name="download_logs"
    )
    outcome = models.CharField(max_length=10, choices=DownloadOutcome.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["animal", "-created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Download {self.outcome} of {self.animal_id} by {self.profile_id} at {self.created_at}"  # type: ignore
