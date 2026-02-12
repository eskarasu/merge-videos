import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.datastructures import MultiValueDict

from video_merge.application.use_cases import CreateMergeJobUseCase
from video_merge.domain.entities import JobStatus
from video_merge.infrastructure.repositories import DjangoMergeJobRepository
from video_merge.models import MergeJob
from video_merge.presentation.forms import MergeJobCreateForm


class MergeJobCreateFormTests(TestCase):
    def test_accepts_multiple_valid_video_files(self) -> None:
        files = MultiValueDict(
            {
                "files": [
                    SimpleUploadedFile("cam1.mp4", b"a", content_type="video/mp4"),
                    SimpleUploadedFile("cam2.mkv", b"b", content_type="video/x-matroska"),
                ]
            }
        )

        form = MergeJobCreateForm(data={"name": "Aksam Maci"}, files=files)

        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data["files"]), 2)

    def test_rejects_unsupported_file_extension(self) -> None:
        files = MultiValueDict(
            {"files": [SimpleUploadedFile("notes.txt", b"content", content_type="text/plain")]}
        )
        form = MergeJobCreateForm(data={"name": "Test"}, files=files)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)


class CreateMergeJobUseCaseTests(TestCase):
    def setUp(self) -> None:
        self._temp_media_root = tempfile.mkdtemp(prefix="video-merge-tests-")
        self._override = override_settings(MEDIA_ROOT=self._temp_media_root)
        self._override.enable()
        self.user = get_user_model().objects.create_user(username="user1", password="secret123")

    def tearDown(self) -> None:
        self._override.disable()
        shutil.rmtree(self._temp_media_root, ignore_errors=True)

    def test_creates_pending_job_with_clip_order(self) -> None:
        repository = DjangoMergeJobRepository()
        use_case = CreateMergeJobUseCase(repository=repository)

        uploaded_files = [
            SimpleUploadedFile("001.mp4", b"fake-video-1", content_type="video/mp4"),
            SimpleUploadedFile("002.mp4", b"fake-video-2", content_type="video/mp4"),
        ]

        job = use_case.execute(owner_id=self.user.id, name="Gun 1", uploaded_files=uploaded_files)

        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(len(job.clips), 2)
        self.assertEqual(job.clips[0].order, 1)
        self.assertEqual(job.clips[1].order, 2)


class DashboardAccessTests(TestCase):
    def test_dashboard_requires_login(self) -> None:
        response = self.client.get(reverse("video_merge:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class DashboardQueueDispatchTests(TestCase):
    def setUp(self) -> None:
        self._temp_media_root = tempfile.mkdtemp(prefix="video-merge-tests-")
        self._override = override_settings(MEDIA_ROOT=self._temp_media_root)
        self._override.enable()
        self.user = get_user_model().objects.create_user(username="queue-user", password="secret123")
        self.client.login(username="queue-user", password="secret123")

    def tearDown(self) -> None:
        self._override.disable()
        shutil.rmtree(self._temp_media_root, ignore_errors=True)

    def test_dashboard_post_enqueues_background_task(self) -> None:
        created_job = SimpleNamespace(id=uuid4())

        with (
            patch("video_merge.presentation.views.MergeJobCreateForm") as mock_form_class,
            patch("video_merge.presentation.views.build_use_case_bundle") as mock_bundle_builder,
        ):
            form = mock_form_class.return_value
            form.is_valid.return_value = True
            form.cleaned_data = {"name": "Aksam Maci", "files": [SimpleNamespace(name="001.mp4")]}

            use_cases = mock_bundle_builder.return_value
            use_cases.create_job.execute.return_value = created_job
            use_cases.enqueue_job.execute.return_value = "task-1"

            response = self.client.post(
                reverse("video_merge:dashboard"),
                data={
                    "name": "Aksam Maci",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("video_merge:job_detail", kwargs={"job_id": created_job.id}))
        use_cases.create_job.execute.assert_called_once()
        use_cases.enqueue_job.execute.assert_called_once_with(owner_id=self.user.id, job_id=created_job.id)

    def test_retry_endpoint_requeues_failed_job(self) -> None:
        job = MergeJob.objects.create(
            owner=self.user,
            name="Retry Job",
            status=MergeJob.Status.FAILED,
            error_message="Onceki hata",
        )

        with patch("video_merge.tasks.process_merge_job_task.delay", return_value=SimpleNamespace(id="task-2")) as mock_delay:
            response = self.client.post(reverse("video_merge:job_retry", kwargs={"job_id": job.id}))

        self.assertEqual(response.status_code, 302)
        self.assertIn(str(job.id), response.url)
        job.refresh_from_db()
        self.assertEqual(job.status, MergeJob.Status.PENDING)
        self.assertEqual(job.error_message, "")
        mock_delay.assert_called_once()
