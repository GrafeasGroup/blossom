"""The views of the API, providing the possible API requests."""
from typing import Dict

import pytz
from django.utils import timezone
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import AdminApiKeyCustomCheck
from api.models import Transcription
from authentication.models import BlossomUser


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
        # subtract 2 from volunteer count for anon volunteer and u/ToR
        return {
            "volunteer_count": BlossomUser.objects.filter(is_volunteer=True).count()
            - 2,
            "transcription_count": Transcription.objects.count(),
            "days_since_inception": (
                timezone.now()
                - pytz.timezone("UTC").localize(
                    timezone.datetime(day=1, month=4, year=2017), is_dst=None
                )
            ).days,
        }


class SummaryView(APIView):
    """A view to request the summary of statistics."""

    permission_classes = (AdminApiKeyCustomCheck,)

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
