from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class VideoClip:
    id: int
    job_id: UUID
    order: int
    original_name: str
    file_path: Path


@dataclass(frozen=True, slots=True)
class MergeJob:
    id: UUID
    owner_id: int
    name: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    output_file_name: str | None = None
    error_message: str = ""
    clips: tuple[VideoClip, ...] = field(default_factory=tuple)

    @property
    def is_finished(self) -> bool:
        return self.status in {JobStatus.COMPLETED, JobStatus.FAILED}

