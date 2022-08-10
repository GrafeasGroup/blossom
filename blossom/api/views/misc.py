"""Views that don't fit in any of the other view files."""
import datetime
from typing import Dict

import pytz
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from blossom.api.authentication import AdminApiKeyCustomCheck
from blossom.api.helpers import get_time_since_open
from blossom.api.models import Submission
from blossom.authentication.models import BlossomUser


class Summary(object):
    """A basic object that just generates a summary view that's easy to access."""

    @staticmethod
    def generate_summary() -> Dict:
        """
        Generate a summary based on the current state of the system.

        The summary is a dictionary consisting of the following elements:
        - volunteer_count: the number of volunteers
        - transcription_count: the number of transcriptions
        - days_since_inception: the number of days since the first of April 2017

        :return: A dictionary containing the three key-value pairs as described
        """
        date_minus_two_weeks = datetime.datetime.now(tz=pytz.utc) - datetime.timedelta(
            weeks=2
        )
        return {
            "volunteer_count": BlossomUser.objects.filter(
                is_volunteer=True, is_bot=False
            ).count(),
            "active_volunteer_count": Submission.objects.filter(
                completed_by__isnull=False,
                complete_time__gte=date_minus_two_weeks,
            )
            .values("completed_by")
            .distinct()
            .count(),
            "transcription_count": Submission.objects.filter(
                completed_by__isnull=False
            ).count(),
            "days_since_inception": get_time_since_open(days=True),
        }


class SummaryView(APIView):
    """A view to request the summary of statistics."""

    permission_classes = (AdminApiKeyCustomCheck,)

    @csrf_exempt
    @swagger_auto_schema(
        responses={
            200: DocResponse(
                "Successful summary provision",
                schema=Schema(
                    type="object",
                    properties={
                        "volunteer_count": Schema(type="int"),
                        "transcription_count": Schema(type="int"),
                        "days_since_inception": Schema(type="int"),
                    },
                ),
            )
        }
    )
    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Get a summary of statistics on volunteers and transcriptions."""
        return Response(data=Summary().generate_summary(), status=status.HTTP_200_OK)


class PingView(APIView):
    """View to check whether the service is responsive."""

    permission_classes = (AllowAny,)

    @csrf_exempt
    @swagger_auto_schema(
        responses={
            200: DocResponse(
                "Successful pong",
                schema=Schema(
                    type="object", properties={"ping!": Schema(type="string")}
                ),
            )
        }
    )
    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Ping the server."""
        return Response({"ping?!": "PONG"}, status=status.HTTP_200_OK)
