"""The views of the API, providing the possible API requests."""
import random
from datetime import timedelta

from django.conf import settings
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter, Response as DocResponse, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.authentication import AdminApiKeyCustomCheck
from api.helpers import validate_request
from api.models import Source, Submission, Transcription
from api.serializers import SubmissionSerializer
from authentication.models import BlossomUser
from blossom.slack_conn.helpers import client as slack


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Get information on all submissions or a specific"
        " submission if specified.",
        operation_description="Include the original_id as a query to filter"
        " the submissions on the specified ID.",
        manual_parameters=[Parameter("original_id", "query", type="string")],
    ),
)
class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self) -> QuerySet:
        """
        Get information on all submissions or a specific submission if specified.

        When a original_id is provided as a query parameter, filter the
        queryset on that submission.
        """
        queryset = Submission.objects.all().order_by("id")
        if "original_id" in self.request.query_params:
            queryset = queryset.filter(
                original_id=self.request.query_params["original_id"]
            )
        return queryset

    @swagger_auto_schema(
        manual_parameters=[Parameter("ctq", "query", type="boolean")],
        responses={200: DocResponse("Successful operation", schema=serializer_class)},
    )
    @action(detail=False, methods=["get"])
    def expired(self, request: Request) -> Response:
        """
        Return all old submissions that have not been claimed or completed yet.

        A set definition for old is when a Submission has been submitted 18
        hours or longer ago. If the query string of ctq is passed in with a
        value of True then return all posts that have not been completed or
        claimed.

        When no posts are found, an empty array is returned in the body.
        """
        if request.query_params.get("ctq", False):
            delay_time = timezone.now()
        else:
            delay_time = timezone.now() - timedelta(hours=settings.ARCHIVIST_DELAY_TIME)
        queryset = Submission.objects.filter(
            completed_by=None,
            claimed_by=None,
            create_time__lt=delay_time,
            archived=False,
        )
        return Response(
            self.get_serializer(queryset, many=True, context={"request", request}).data
        )

    @swagger_auto_schema(
        responses={200: DocResponse("Successful operation", schema=serializer_class)}
    )
    @action(detail=False, methods=["get"])
    def unarchived(self, request: Request) -> Response:
        """
        Return all completed old submissions which are not archived.

        The definition of old in this method is half an hour. When no posts are
        found, an empty array is returned in the body.
        """
        delay_time = timezone.now() - timedelta(
            hours=settings.ARCHIVIST_COMPLETED_DELAY_TIME
        )
        queryset = Submission.objects.filter(
            ~Q(completed_by=None) & Q(complete_time__lt=delay_time) & Q(archived=False)
        )
        return Response(data=self.get_serializer(queryset, many=True).data)

    @swagger_auto_schema(
        request_body=Schema(
            type="object", properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse("Successful unclaim operation", schema=serializer_class),
            400: "The volunteer username is not provided",
            404: "The specified volunteer or submission is not found",
            406: "The specified volunteer has not claimed the specified submission",
            409: "The submission has already been completed",
            412: "The submission has not yet been claimed",
        },
    )
    @validate_request(data_params={"username"})
    @action(detail=True, methods=["patch"])
    def unclaim(self, request: Request, pk: int, username: str = None) -> Response:
        """
        Unclaim the specified submission, from the specified volunteer.

        The volunteer is specified in the HTTP body.
        """
        submission = get_object_or_404(Submission, id=pk)
        user = get_object_or_404(BlossomUser, username=username)

        if submission.claimed_by is None:
            return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        if submission.claimed_by != user:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        if submission.completed_by is not None:
            return Response(status=status.HTTP_409_CONFLICT)

        submission.claimed_by = None
        submission.claim_time = None
        submission.save()
        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @swagger_auto_schema(
        request_body=Schema(
            type="object", properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse("Successful claim operation", schema=serializer_class),
            400: "The volunteer username is not provided",
            404: "The specified volunteer or submission is not found",
            409: "The submission is already claimed",
        },
    )
    @validate_request(data_params={"username"})
    @action(detail=True, methods=["patch"])
    def claim(self, request: Request, pk: int, username: str = None) -> Response:
        """
        Claim the specified submission from the specified volunteer.

        The volunteer is specified in the HTTP body.
        """
        submission = get_object_or_404(Submission, id=pk)
        user = get_object_or_404(BlossomUser, username=username)

        if submission.claimed_by is not None:
            return Response(status=status.HTTP_409_CONFLICT)

        submission.claimed_by = user
        submission.claim_time = timezone.now()
        submission.save()

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @staticmethod
    def _should_check_transcription(volunteer: BlossomUser) -> bool:
        """
        Return whether a transcription should be checked based on user gamma.

        This is based on the gamma of the user. Given this gamma, a probability
        for the check is provided. The following probabilities are in use:

        - gamma <= 50:              0.8
        - 50 < gamma <= 100:        0.7
        - 100 < gamma <= 250:       0.6
        - 250 < gamma <= 500:       0.5
        - 500 < gamma <= 1000:      0.3
        - 1000 <= gamma <= 5000:    0.1
        - 5000 < gamma:             0.05

        :param volunteer:   the volunteer for which the post should be checked
        :return:            whether the post has to be checked
        """
        probabilities = [
            (50, 0.8),
            (100, 0.7),
            (250, 0.6),
            (500, 0.5),
            (1000, 0.3),
            (5000, 0.1),
        ]
        for (gamma, probability) in probabilities:
            if volunteer.gamma <= gamma:
                if random.random() < probability:
                    return True
                else:
                    return False
        return random.random() < 0.05

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            required=["username"],
            properties={
                "username": Schema(type="string"),
                "mod_override": Schema(type="boolean"),
            },
        ),
        responses={
            201: DocResponse("Successful done operation", schema=serializer_class),
            400: "The volunteer username is not provided",
            404: "The specified volunteer or submission is not found",
            409: "The submission is already completed",
            412: "The submission is not claimed or claimed by someone else",
        },
    )
    @validate_request(data_params={"username"})
    @action(detail=True, methods=["patch"])
    def done(self, request: Request, pk: int, username: str = None) -> Response:
        """
        Mark the submission as done from the specified volunteer.

        When "mod_override" is provided as a field in the HTTP body and is true,
        and the requesting user is a mod, then the check of whether the
        completing volunteer is the volunteer that claimed the submission is
        skipped.

        Note that this API call has a certain chance to send a message to
        Slack for the random check of this transcription.
        """
        submission = get_object_or_404(Submission, id=pk)
        user = get_object_or_404(BlossomUser, username=username)

        if submission.completed_by is not None:
            return Response(status=status.HTTP_409_CONFLICT)

        if submission.claimed_by is None:
            return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        mod_override = (
            request.data.get("mod_override", False) and request.user.is_grafeas_staff
        )

        if not mod_override:
            if submission.claimed_by != user:
                return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        submission.completed_by = user
        submission.complete_time = timezone.now()
        submission.save()

        if self._should_check_transcription(user):
            transcription = Transcription.objects.filter(submission=submission)
            url = transcription.first().url if transcription else submission.tor_url
            slack.chat_postMessage(
                channel="#transcription_check",
                text="Please check the following transcription of "
                f"u/{user.username}: {url}.",
            )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            required=["original_id", "source"],
            properties={
                "original_id": Schema(type="string"),
                "source": Schema(type="string"),
                "url": Schema(type="string"),
                "tor_url": Schema(type="string"),
            },
        ),
        responses={
            201: DocResponse("Successful creation", schema=serializer_class),
            400: "Required parameters not provided",
            404: "Source requested was not found",
        },
    )
    @validate_request(data_params={"original_id", "source"})
    def create(
        self,
        request: Request,
        original_id: str = None,
        source: str = None,
        *args: object,
        **kwargs: object,
    ) -> Response:
        """
        Create a new submission.

        Note that both the original id and the source should be supplied.
        """
        source_obj = get_object_or_404(Source, pk=source)
        url = request.data.get("url")
        tor_url = request.data.get("tor_url")
        submission = Submission.objects.create(
            original_id=original_id, source=source_obj, url=url, tor_url=tor_url
        )
        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )
