from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from video_merge.application.use_cases import (
    CreateMergeJobUseCase,
    EnqueueMergeJobUseCase,
    GetUserJobUseCase,
    ListUserJobsUseCase,
    ProcessMergeJobUseCase,
)
from video_merge.infrastructure.ffmpeg_merger import FFmpegVideoMerger
from video_merge.infrastructure.queue import CeleryMergeJobQueue
from video_merge.infrastructure.repositories import DjangoMergeJobRepository


@dataclass(frozen=True)
class UseCaseBundle:
    create_job: CreateMergeJobUseCase
    enqueue_job: EnqueueMergeJobUseCase
    process_job: ProcessMergeJobUseCase
    list_jobs: ListUserJobsUseCase
    get_job: GetUserJobUseCase


def build_use_case_bundle() -> UseCaseBundle:
    repository = DjangoMergeJobRepository()
    queue = CeleryMergeJobQueue()
    merger = FFmpegVideoMerger(ffmpeg_binary=getattr(settings, "FFMPEG_BINARY", "ffmpeg"))
    media_root = Path(settings.MEDIA_ROOT)

    return UseCaseBundle(
        create_job=CreateMergeJobUseCase(repository=repository),
        enqueue_job=EnqueueMergeJobUseCase(repository=repository, queue=queue),
        process_job=ProcessMergeJobUseCase(
            repository=repository,
            merger=merger,
            media_root=media_root,
        ),
        list_jobs=ListUserJobsUseCase(repository=repository),
        get_job=GetUserJobUseCase(repository=repository),
    )
