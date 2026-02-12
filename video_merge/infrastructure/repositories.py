from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.urls import reverse

from video_merge.domain.entities import JobStatus, MergeJob, VideoClip
from video_merge.domain.interfaces import MergeJobRepository
from video_merge.models import MergeClip, MergeJob as MergeJobModel
from video_merge.presentation.ws_groups import user_jobs_group_name

logger = logging.getLogger(__name__)


def _clip_to_entity(clip: MergeClip) -> VideoClip:
    return VideoClip(
        id=clip.id,
        job_id=clip.job_id,
        order=clip.order,
        original_name=clip.original_name,
        file_path=Path(clip.file.path),
    )


def _job_to_entity(job: MergeJobModel, include_clips: bool = False) -> MergeJob:
    clips: tuple[VideoClip, ...] = tuple()
    if include_clips:
        clips = tuple(_clip_to_entity(clip) for clip in job.clips.all())

    return MergeJob(
        id=job.id,
        owner_id=job.owner_id,
        name=job.name,
        status=JobStatus(job.status),
        created_at=job.created_at,
        updated_at=job.updated_at,
        output_file_name=job.output_file.name if job.output_file else None,
        error_message=job.error_message,
        clips=clips,
    )


def _serialize_job_update(job: MergeJobModel) -> dict[str, object]:
    return {
        "job_id": str(job.id),
        "status": job.status,
        "error_message": job.error_message or "",
        "has_output": bool(job.output_file),
        "output_url": (
            reverse("video_merge:job_download", kwargs={"job_id": job.id})
            if job.output_file
            else ""
        ),
    }


def _publish_job_update(job: MergeJobModel) -> None:
    if not getattr(settings, "REALTIME_UPDATES_ENABLED", False):
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    group_name = user_jobs_group_name(job.owner_id)
    event = {
        "type": "job.status.event",
        "payload": _serialize_job_update(job),
    }

    try:
        async_to_sync(channel_layer.group_send)(group_name, event)
    except Exception:  # noqa: BLE001
        logger.warning("Job status event publish failed for job_id=%s", job.id, exc_info=True)


class DjangoMergeJobRepository(MergeJobRepository):
    def create_job(self, owner_id: int, name: str) -> MergeJob:
        job = MergeJobModel.objects.create(owner_id=owner_id, name=name)
        return _job_to_entity(job)

    @transaction.atomic
    def add_clip(self, job_id: UUID, uploaded_file: object, order: int, original_name: str) -> VideoClip:
        job = MergeJobModel.objects.select_for_update().get(id=job_id)
        clip = MergeClip(job=job, order=order, original_name=original_name)
        clip.file.save(original_name, uploaded_file, save=False)
        clip.save()
        return _clip_to_entity(clip)

    def get_user_job(self, user_id: int, job_id: UUID, include_clips: bool = False) -> MergeJob | None:
        queryset = MergeJobModel.objects.filter(owner_id=user_id, id=job_id)
        if include_clips:
            queryset = queryset.prefetch_related(
                Prefetch("clips", queryset=MergeClip.objects.order_by("order"))
            )

        job = queryset.first()
        if job is None:
            return None

        return _job_to_entity(job, include_clips=include_clips)

    def list_user_jobs(self, user_id: int) -> list[MergeJob]:
        jobs = MergeJobModel.objects.filter(owner_id=user_id)
        return [_job_to_entity(job, include_clips=False) for job in jobs]

    def list_job_clips(self, job_id: UUID) -> list[VideoClip]:
        clips = MergeClip.objects.filter(job_id=job_id).order_by("order")
        return [_clip_to_entity(clip) for clip in clips]

    def set_status(self, job_id: UUID, status: JobStatus, error_message: str = "") -> None:
        updated_count = MergeJobModel.objects.filter(id=job_id).update(
            status=status.value,
            error_message=error_message,
        )
        if not updated_count:
            return

        job = MergeJobModel.objects.only("id", "owner_id", "status", "error_message", "output_file").get(id=job_id)
        _publish_job_update(job)

    def set_output_file(self, job_id: UUID, output_file_name: str) -> None:
        MergeJobModel.objects.filter(id=job_id).update(output_file=output_file_name)
