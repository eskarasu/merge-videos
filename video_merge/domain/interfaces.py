from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable
from uuid import UUID

from .entities import JobStatus, MergeJob, VideoClip


class MergeJobRepository(ABC):
    @abstractmethod
    def create_job(self, owner_id: int, name: str) -> MergeJob:
        raise NotImplementedError

    @abstractmethod
    def add_clip(self, job_id: UUID, uploaded_file: object, order: int, original_name: str) -> VideoClip:
        raise NotImplementedError

    @abstractmethod
    def get_user_job(self, user_id: int, job_id: UUID, include_clips: bool = False) -> MergeJob | None:
        raise NotImplementedError

    @abstractmethod
    def list_user_jobs(self, user_id: int) -> list[MergeJob]:
        raise NotImplementedError

    @abstractmethod
    def list_job_clips(self, job_id: UUID) -> list[VideoClip]:
        raise NotImplementedError

    @abstractmethod
    def set_status(self, job_id: UUID, status: JobStatus, error_message: str = "") -> None:
        raise NotImplementedError

    @abstractmethod
    def set_output_file(self, job_id: UUID, output_file_name: str) -> None:
        raise NotImplementedError


class VideoMerger(ABC):
    @abstractmethod
    def merge(self, clip_paths: Iterable[Path], output_path: Path) -> None:
        raise NotImplementedError


class MergeJobQueue(ABC):
    @abstractmethod
    def enqueue_process_job(self, owner_id: int, job_id: UUID) -> str:
        raise NotImplementedError
