"""The views of the API, providing the possible API requests."""
import json
import random
import uuid
from datetime import timedelta
from typing import Dict

import pytz
from django.conf import settings
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import AdminApiKeyCustomCheck
from api.helpers import validate_request
from api.models import Source, Submission, Transcription
from api.serializers import (
    SourceSerializer,
    SubmissionSerializer,
    TranscriptionSerializer,
    VolunteerSerializer,
)
from api.slack_helpers import client as slack
from api.slack_helpers import (
    is_valid_github_request,
    process_message,
    send_github_sponsors_message,
)
from authentication.models import BlossomUser


@csrf_exempt
def slack_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Handle post requests from Slack.

    Slack plays a lot of games with its API and honestly it's one of the
    most frustrating things I've ever worked with. There are a couple of
    things that we'll need to do in this view:

    * No matter what, respond within three seconds _of slack sending the
      ping_ -- we really have less than three seconds. Slack is impatient.
      Slack cares not for your feelings.
    * Sometimes we'll get a challenge that we have to respond to, but it's
      unclear if we'll only get it during setup or whenever Slack feels
      like it.

    So how do we get around Slack's ridiculous timeouts?

    ⋆ . ˚ * ✧ T H R E A D I N G ✧ * ˚ . ⋆
    -------------------------------------

    We extract the information we need out of the request, pass it off
    to a different function to actually figure out what the hell Slack
    wants, and then send our own response. In the meantime, we basically
    just send a 200 OK as fast as we can so that Slack doesn't screw up
    our day.

    :param request: HttpRequest
    :return: HttpRequest
    """
    json_data = json.loads(request.body)
    if json_data.get("challenge"):
        # looks like we got hit with the magic handshake packet. Send it
        # back to its maker.
        return HttpResponse(json_data["challenge"])
    # It's not a challenge, so just hand off data processing to the
    # thread and give Slack the result it craves.
    process_message(json_data)
    return HttpResponse(status=200)


@csrf_exempt
def github_sponsors_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Translate GitHub Sponsors webhook to Slack webhook.

    GitHub does not provide the ability to change the format of their webhooks,
    so we have to provide a translation layer. This function is an adaptation
    of alexellis' work linked below.

    resources:
    - https://developer.github.com/webhooks/event-payloads/#sponsorship
    - https://github.com/alexellis/sponsors-functions/blob/master/
        sponsors-receiver/handler.js
    """
    if not is_valid_github_request(request):
        # Don't know what it was, but it wasn't legit. Just say everything's groovy.
        return HttpResponse(status=200)

    data = json.loads(request.body.decode())

    if action := data.get("action"):
        send_github_sponsors_message(data, action)
    return HttpResponse(status=200)
