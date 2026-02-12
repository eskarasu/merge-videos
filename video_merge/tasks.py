from __future__ import annotations

import logging
from uuid import UUID

from celery import shared_task

from video_merge.domain.exceptions import JobNotFoundError
from video_merge.infrastructure.container import build_use_case_bundle

logger = logging.getLogger(__name__)


@shared_task(name="video_merge.process_merge_job")
def process_merge_job_task(owner_id: int, job_id: str) -> None:
    use_cases = build_use_case_bundle()
    try:
        use_cases.process_job.execute(owner_id=owner_id, job_id=UUID(job_id))
    except JobNotFoundError:
        logger.exception("Merge job bulunamadi. owner_id=%s job_id=%s", owner_id, job_id)
        raise
    except Exception:
        logger.exception("Merge job isleme hatasi. owner_id=%s job_id=%s", owner_id, job_id)
        raise

