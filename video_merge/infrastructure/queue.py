from __future__ import annotations

from uuid import UUID

from kombu.exceptions import OperationalError

from video_merge.domain.exceptions import QueueUnavailableError
from video_merge.domain.interfaces import MergeJobQueue


class CeleryMergeJobQueue(MergeJobQueue):
    def enqueue_process_job(self, owner_id: int, job_id: UUID) -> str:
        from video_merge.tasks import process_merge_job_task

        try:
            result = process_merge_job_task.delay(owner_id=owner_id, job_id=str(job_id))
        except OperationalError as exc:
            raise QueueUnavailableError("Redis/Celery kuyruguna baglanilamadi.") from exc

        return result.id

