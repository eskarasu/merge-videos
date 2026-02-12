from __future__ import annotations

from pathlib import Path
from uuid import UUID

from video_merge.domain.constants import SUPPORTED_VIDEO_EXTENSIONS
from video_merge.domain.entities import JobStatus, MergeJob
from video_merge.domain.exceptions import InvalidInputError, JobNotFoundError, QueueUnavailableError
from video_merge.domain.interfaces import MergeJobQueue, MergeJobRepository, VideoMerger


class CreateMergeJobUseCase:
    def __init__(self, repository: MergeJobRepository) -> None:
        self._repository = repository

    def execute(self, owner_id: int, name: str, uploaded_files: list[object]) -> MergeJob:
        if not uploaded_files:
            raise InvalidInputError("En az bir video dosyasi yuklenmelidir.")

        normalized_name = name.strip() if name else ""
        if not normalized_name:
            normalized_name = "Video Birlestirme"

        validated_files: list[tuple[object, str]] = []
        for index, uploaded_file in enumerate(uploaded_files, start=1):
            filename = getattr(uploaded_file, "name", f"clip_{index}.mp4")
            extension = Path(filename).suffix.lower()
            if extension not in SUPPORTED_VIDEO_EXTENSIONS:
                raise InvalidInputError(f"Desteklenmeyen dosya uzantisi: {extension}")
            validated_files.append((uploaded_file, filename))

        job = self._repository.create_job(owner_id=owner_id, name=normalized_name)

        for index, (uploaded_file, filename) in enumerate(validated_files, start=1):
            self._repository.add_clip(
                job_id=job.id,
                uploaded_file=uploaded_file,
                order=index,
                original_name=filename,
            )

        persisted_job = self._repository.get_user_job(owner_id, job.id, include_clips=True)
        if persisted_job is None:
            raise JobNotFoundError("Olusturulan is geri okunamadi.")
        return persisted_job


class ProcessMergeJobUseCase:
    def __init__(
        self,
        repository: MergeJobRepository,
        merger: VideoMerger,
        media_root: Path,
    ) -> None:
        self._repository = repository
        self._merger = merger
        self._media_root = media_root

    def execute(self, owner_id: int, job_id: UUID) -> MergeJob:
        job = self._repository.get_user_job(owner_id, job_id, include_clips=True)
        if job is None:
            raise JobNotFoundError("Is bulunamadi.")

        clips = self._repository.list_job_clips(job_id)
        if not clips:
            message = "Birlestirme icin video bulunamadi."
            self._repository.set_status(job_id, JobStatus.FAILED, error_message=message)
            raise InvalidInputError(message)

        self._repository.set_status(job_id, JobStatus.RUNNING, error_message="")

        output_relative = Path("merged_outputs") / f"user_{owner_id}" / f"{job_id}.mp4"
        output_absolute = self._media_root / output_relative

        try:
            self._merger.merge(
                clip_paths=[clip.file_path for clip in clips],
                output_path=output_absolute,
            )
        except Exception as exc:
            self._repository.set_status(job_id, JobStatus.FAILED, error_message=str(exc))
            raise

        self._repository.set_output_file(job_id, output_relative.as_posix())
        self._repository.set_status(job_id, JobStatus.COMPLETED, error_message="")

        completed_job = self._repository.get_user_job(owner_id, job_id, include_clips=True)
        if completed_job is None:
            raise JobNotFoundError("Islem tamamlandi ancak kayit bulunamadi.")
        return completed_job


class EnqueueMergeJobUseCase:
    def __init__(self, repository: MergeJobRepository, queue: MergeJobQueue) -> None:
        self._repository = repository
        self._queue = queue

    def execute(self, owner_id: int, job_id: UUID) -> str:
        job = self._repository.get_user_job(owner_id, job_id, include_clips=False)
        if job is None:
            raise JobNotFoundError("Kuyruga alinacak is bulunamadi.")

        if job.status == JobStatus.RUNNING:
            raise InvalidInputError("Bu is zaten isleniyor.")
        if job.status == JobStatus.COMPLETED and job.output_file_name:
            raise InvalidInputError("Bu is zaten tamamlanmis.")

        self._repository.set_status(job_id, JobStatus.PENDING, error_message="")
        try:
            task_id = self._queue.enqueue_process_job(owner_id=owner_id, job_id=job_id)
        except QueueUnavailableError as exc:
            self._repository.set_status(job_id, JobStatus.FAILED, error_message=str(exc))
            raise

        return task_id


class ListUserJobsUseCase:
    def __init__(self, repository: MergeJobRepository) -> None:
        self._repository = repository

    def execute(self, user_id: int) -> list[MergeJob]:
        return self._repository.list_user_jobs(user_id)


class GetUserJobUseCase:
    def __init__(self, repository: MergeJobRepository) -> None:
        self._repository = repository

    def execute(self, user_id: int, job_id: UUID, include_clips: bool = True) -> MergeJob | None:
        return self._repository.get_user_job(user_id=user_id, job_id=job_id, include_clips=include_clips)
