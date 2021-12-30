from django.conf import settings
from django.http import HttpRequest


def app_enable_check(request: HttpRequest) -> dict:
    """Add the "enable app" flag to template processing."""
    return {"ENABLE_APP": settings.ENABLE_APP}
