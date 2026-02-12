from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def clip_upload_path(instance: "MergeClip", filename: str) -> str:
    extension = Path(filename).suffix
    clean_name = Path(filename).stem.replace(" ", "_")
    return (
        f"uploads/user_{instance.job.owner_id}/job_{instance.job_id}/clips/"
        f"{instance.order:04d}_{clean_name}{extension}"
    )


class MergeJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merge_jobs",
    )
    name = models.CharField(max_length=150)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    output_file = models.FileField(upload_to="merged_outputs/", blank=True, null=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner})"


class MergeClip(models.Model):
    job = models.ForeignKey(
        MergeJob,
        on_delete=models.CASCADE,
        related_name="clips",
    )
    file = models.FileField(upload_to=clip_upload_path)
    original_name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["job", "order"], name="uniq_job_clip_order"),
        ]

    def __str__(self) -> str:
        return f"{self.job_id} - #{self.order} - {self.original_name}"
