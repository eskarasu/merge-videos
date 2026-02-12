from django.urls import path

from video_merge.presentation.consumers import JobStatusConsumer

websocket_urlpatterns = [
    path("ws/jobs/", JobStatusConsumer.as_asgi()),
]

