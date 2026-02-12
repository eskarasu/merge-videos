from __future__ import annotations

from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView

from video_merge.domain.exceptions import (
    InvalidInputError,
    QueueUnavailableError,
)
from video_merge.infrastructure.container import build_use_case_bundle
from video_merge.presentation.forms import MergeJobCreateForm, SignUpForm


class DashboardView(LoginRequiredMixin, View):
    template_name = "video_merge/dashboard.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        use_cases = build_use_case_bundle()
        context = {
            "form": MergeJobCreateForm(),
            "jobs": use_cases.list_jobs.execute(request.user.id),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        form = MergeJobCreateForm(request.POST, request.FILES)
        use_cases = build_use_case_bundle()

        if not form.is_valid():
            context = {
                "form": form,
                "jobs": use_cases.list_jobs.execute(request.user.id),
            }
            return render(request, self.template_name, context)

        files = form.cleaned_data["files"]
        try:
            created_job = use_cases.create_job.execute(
                owner_id=request.user.id,
                name=form.cleaned_data["name"],
                uploaded_files=files,
            )
            use_cases.enqueue_job.execute(owner_id=request.user.id, job_id=created_job.id)
            messages.success(request, "Islem kuyruga alindi. Durumu detay ekranindan takip edebilirsiniz.")
            return redirect("video_merge:job_detail", job_id=created_job.id)
        except InvalidInputError as exc:
            form.add_error("files", str(exc))
        except QueueUnavailableError as exc:
            form.add_error(None, f"Kuyruk baglantisi basarisiz: {exc}")
        except Exception as exc:  # noqa: BLE001
            form.add_error(None, f"Beklenmeyen hata: {exc}")

        context = {
            "form": form,
            "jobs": use_cases.list_jobs.execute(request.user.id),
        }
        return render(request, self.template_name, context)


class JobDetailView(LoginRequiredMixin, View):
    template_name = "video_merge/job_detail.html"

    def get(self, request: HttpRequest, job_id: UUID) -> HttpResponse:
        use_cases = build_use_case_bundle()
        job = use_cases.get_job.execute(user_id=request.user.id, job_id=job_id, include_clips=True)
        if job is None:
            raise Http404("Is bulunamadi.")

        context = {
            "job": job,
        }
        return render(request, self.template_name, context)


class JobOutputDownloadView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, job_id: UUID) -> FileResponse:
        use_cases = build_use_case_bundle()
        job = use_cases.get_job.execute(user_id=request.user.id, job_id=job_id, include_clips=False)
        if job is None:
            raise Http404("Is bulunamadi.")
        if not job.output_file_name:
            raise Http404("Bu is icin indirilebilir cikti yok.")

        absolute_path = Path(settings.MEDIA_ROOT) / job.output_file_name
        if not absolute_path.exists():
            raise Http404("Cikti dosyasi diskte bulunamadi.")

        download_name = f"{job.name}.mp4".replace(" ", "_")
        return FileResponse(absolute_path.open("rb"), as_attachment=True, filename=download_name)


class RetryJobView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, job_id: UUID) -> HttpResponse:
        use_cases = build_use_case_bundle()
        try:
            use_cases.enqueue_job.execute(owner_id=request.user.id, job_id=job_id)
            messages.success(request, "Is yeniden kuyruga alindi.")
        except InvalidInputError as exc:
            messages.error(request, str(exc))
        except QueueUnavailableError as exc:
            messages.error(request, f"Kuyruk baglantisi basarisiz: {exc}")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Beklenmeyen hata: {exc}")

        return redirect("video_merge:job_detail", job_id=job_id)


class SignUpView(SuccessMessageMixin, CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")
    success_message = "Hesabiniz olusturuldu. Simdi giris yapabilirsiniz."
