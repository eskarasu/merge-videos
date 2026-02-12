from django.urls import path

from video_merge.presentation.views import (
    DashboardView,
    JobDetailView,
    JobOutputDownloadView,
    RetryJobView,
    SignUpView,
)

app_name = "video_merge"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("jobs/<uuid:job_id>/", JobDetailView.as_view(), name="job_detail"),
    path("jobs/<uuid:job_id>/download/", JobOutputDownloadView.as_view(), name="job_download"),
    path("jobs/<uuid:job_id>/retry/", RetryJobView.as_view(), name="job_retry"),
]
