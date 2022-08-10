import json

import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from ipware import get_client_ip
from rest_framework import status
from rest_framework.request import Request


@csrf_exempt
def plausible_event(request: Request) -> HttpResponse:
    """Handle events from plausible.io's JS that we run."""
    headers = {
        "user-agent": request.headers.get("user-agent"),
        "x-forwarded-for": get_client_ip(request)[0],
    }

    requests.post(
        "https://plausible.io/api/event",
        headers=headers,
        data=json.loads(request.body),
        timeout=2,
    )

    return HttpResponse(status=status.HTTP_200_OK)
