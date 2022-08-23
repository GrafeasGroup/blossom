"""Views that specifically relate to transcriptions."""
import random
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from blossom.api.authentication import BlossomApiPermission
from blossom.api.helpers import validate_request
from blossom.api.models import Source, Submission, Transcription
from blossom.api.serializers import TranscriptionSerializer
from blossom.authentication.models import BlossomUser


class TranscriptionViewSet(viewsets.ModelViewSet):
    """The API view to view and edit information regarding Transcribers."""

    queryset = Transcription.objects.all().order_by("-create_time")
    serializer_class = TranscriptionSerializer
    permission_classes = (BlossomApiPermission,)
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        "id": ["exact"],
        "submission": ["exact"],
        "author": ["exact"],
        "original_id": ["exact", "isnull"],
        "source": ["exact"],
        "url": ["exact", "isnull"],
        "text": ["isnull", "icontains"],
        "removed_from_reddit": ["exact"],
        "create_time": ["gt", "gte", "lte", "lt"],
    }
    ordering_fields = [
        "id",
        "create_time",
        "last_update_time",
    ]

    @csrf_exempt
    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            required=[
                "original_id",
                "source",
                "submission_id",
                "text",
                "url",
                "username",
            ],
            properties={
                "original_id": Schema(type="string"),
                "removed_from_reddit": Schema(type="string"),
                "create_time": Schema(type="string"),
                "source": Schema(type="string"),
                "submission_id": Schema(type="string"),
                "text": Schema(type="string"),
                "url": Schema(type="string"),
                "username": Schema(type="string"),
            },
        ),
        responses={
            201: DocResponse(
                "Successful transcription creation", schema=serializer_class
            ),
            400: "The request does not adhere to the specified HTTP body",
            403: "The volunteer has not accepted the Code of Conduct",
            404: "Either the specified submission or volunteer is not found",
            423: "The user is blocked",
        },
    )
    @validate_request(
        data_params={
            "original_id",
            "submission_id",
            "source",
            "text",
            "url",
            "username",
        }
    )
    def create(
        self,
        request: Request,
        original_id: str = None,
        source: str = None,
        submission_id: str = None,
        text: str = None,
        url: str = None,
        username: str = None,
        *args: object,
        **kwargs: object,
    ) -> Response:
        """
        Create a new transcription.

        The following fields are passed in the HTTP Body:
            - original_id           the base36 ID of the comment
            - source                the system which has submitted this request
            - submission_id         the ID of the corresponding submission
            - text                  the text of the transcription
            - url                   the direct url to the transcription
            - username              the ID or username of the authoring volunteer
            - removed_from_reddit   whether the transcription is removed from Reddit
        """
        # todo: if the original_id is passed in here, make sure this is okay
        submission = get_object_or_404(Submission, id=submission_id)
        user = get_object_or_404(BlossomUser, username=username)
        source = get_object_or_404(Source, name=source)
        removed_from_reddit = request.data.get("removed_from_reddit", "False") == "True"

        if user.blocked:
            return Response(status=status.HTTP_423_LOCKED)

        if not user.accepted_coc:
            return Response(status=status.HTTP_403_FORBIDDEN)

        transcription_create_data = {
            "submission": submission,
            "author": user,
            "original_id": original_id,
            "url": url,
            "source": source,
            "text": text,
            "removed_from_reddit": removed_from_reddit,
        }
        if create_time := request.data.get("create_time"):
            transcription_create_data.update({"create_time": create_time})

        transcription = Transcription.objects.create(**transcription_create_data)
        return Response(
            data=self.serializer_class(
                transcription, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @csrf_exempt
    @swagger_auto_schema(
        manual_parameters=[Parameter("submission_id", "query", type="string")],
        responses={400: 'Query parameter "submission_id" not present'},
    )
    @validate_request(query_params={"submission_id"})
    @action(detail=False, methods=["get"])
    def search(
        self,
        request: Request,
        submission_id: str = None,
        *args: object,
        **kwargs: object,
    ) -> Response:
        """
        Search for the transcriptions of a specific submission.

        Note that providing the id of the submission as a query parameter is mandatory.
        """
        queryset = Transcription.objects.filter(submission__id=submission_id)
        return Response(
            data=self.serializer_class(
                queryset, many=True, context={"request": request}
            ).data
        )

    @csrf_exempt
    @swagger_auto_schema(
        responses={
            200: DocResponse(
                "Successful retrieval of a random transcription",
                schema=serializer_class,
            )
        }
    )
    @action(detail=False, methods=["get"])
    def review_random(
        self, request: Request, *args: object, **kwargs: object
    ) -> Response:
        """
        Pull a random transcription that was completed in the last hour and return it.

        Note that if there are no transcriptions in the last hour, this request
        returns an empty HTTP body.
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)

        queryset = Transcription.objects.filter(create_time__gte=one_hour_ago)

        # TODO: Add system so that we're not pulling the same one over and over

        if not queryset:
            return Response()
        else:
            return Response(
                data=self.serializer_class(
                    random.choice(queryset), context={"request": request}
                ).data
            )
