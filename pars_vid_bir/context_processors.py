from django.conf import settings


def feature_flags(request):  # noqa: ARG001
    return {
        "REALTIME_UPDATES_ENABLED": settings.REALTIME_UPDATES_ENABLED,
        "USE_REDIS": settings.USE_REDIS,
    }

