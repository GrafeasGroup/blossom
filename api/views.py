"""The views of the API, providing the possible API requests."""
import random
import uuid
from datetime import timedelta
from typing import Dict, Tuple

import pytz
from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter, Response as DocResponse, Schema
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import AdminApiKeyCustomCheck
from api.helpers import RequestDataMixin, VolunteerMixin
from api.models import Submission, Transcription, Source
from api.serializers import (
    SubmissionSerializer,
    TranscriptionSerializer,
    VolunteerSerializer,
    SourceSerializer
)
from authentication.models import BlossomUser
from blossom.slack_conn.helpers import client as slack


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Get information on all volunteers or a specific"
        " volunteer if specified.",
        operation_description="Include the username as a query to filter"
        " the volunteers on the specified username.",
        manual_parameters=[Parameter("username", "query", type="string")],
    ),
)
class VolunteerViewSet(viewsets.ModelViewSet):
    """The API view to view and edit information regarding Volunteers."""

    queryset = BlossomUser.objects.filter(is_volunteer=True).order_by("-join_date")
    serializer_class = VolunteerSerializer
    basename = "volunteer"
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self) -> QuerySet:
        """
        Get information on all volunteers or a specific volunteer if specified.

        Including a username as a query parameter filters the volunteers on the
        specified username.
        """
        queryset = BlossomUser.objects.filter(is_volunteer=True).order_by("id")
        username = self.request.query_params.get("username", None)
        if username is not None:
            queryset = queryset.filter(username=username)
        return queryset

    @swagger_auto_schema(
        manual_parameters=[Parameter("username", "query", type="string")],
        responses={
            400: 'No "username" as a query parameter.',
            404: "No volunteer with the specified username.",
        },
    )
    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """Get information on the volunteer with the provided username."""
        username = request.query_params.get("username", None)
        if not username:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        volunteer = BlossomUser.objects.filter(
            Q(username=username) & Q(is_volunteer=True)
        ).first()
        if not volunteer:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(self.serializer_class(volunteer).data)

    @swagger_auto_schema(
        request_body=no_body, responses={404: "No volunteer with the specified ID."}
    )
    @action(detail=True, methods=["patch"])
    def gamma_plusone(self, request: Request, pk: int) -> Response:
        """
        Add one gamme through a fake completed transcription by the volunteer.

        This method should only be called in the case of erroneous behavior of
        the proper procedure of awarding gamma.
        """
        try:
            volunteer = BlossomUser.objects.get(id=pk)
        except BlossomUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        gamma_plus_one, _ = Source.objects.get_or_create(name="gamma_plus_one")

        dummy_post = Submission.objects.create(
            source=gamma_plus_one, completed_by=volunteer
        )
        Transcription.objects.create(
            submission=dummy_post,
            author=volunteer,
            original_id=str(uuid.uuid4()),
            source=gamma_plus_one,
            text="dummy transcription",
        )
        return Response(self.serializer_class(volunteer).data)

    @swagger_auto_schema(
        request_body=Schema(
            type="object", properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse("Successful creation", schema=serializer_class),
            400: 'No "username" key in the data body',
            422: "There already exists a volunteer with the specified username",
        },
    )
    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Create a new user with the specified username."""
        username = request.data.get("username")

        if not username:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if BlossomUser.objects.filter(username=username).first():
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        volunteer = BlossomUser.objects.create(username=username)
        volunteer.set_unusable_password()

        return Response(
            self.serializer_class(volunteer).data, status=status.HTTP_201_CREATED
        )


class SourceViewSet(viewsets.ModelViewSet):
    """
    The API view to view and edit information regarding Sources.

    This information is required for both Submissions and Transcriptions.
    """

    queryset = Source.objects.all().order_by("pk")
    serializer_class = SourceSerializer
    permission_classes = (AdminApiKeyCustomCheck,)


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
class SubmissionViewSet(viewsets.ModelViewSet, RequestDataMixin, VolunteerMixin):
    """The API view to view and edit information regarding Submissions."""

    queryset = Submission.objects.all().order_by("-post_time")
    serializer_class = SubmissionSerializer
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self) -> QuerySet:
        """
        Get information on all submissions or a specific submission if specified.

        When a original_id is provided as a query parameter, filter the
        queryset on that submission.
        """
        queryset = Submission.objects.all().order_by("id")
        original_id = self.request.query_params.get("original_id", None)
        if original_id is not None:
            queryset = queryset.filter(original_id=original_id)
        return queryset

    def _get_possible_claim_done_errors(
        self, request: Request, pk: int
    ) -> [Tuple[Submission, BlossomUser], Response]:
        """
        Get both the submission and the volunteer from the provided parameters.

        Note that this method either returns a tuple of the specific submission
        and volunteer, or an error Response if an error has been encountered
        during lookup.

        Returned error responses are the following:
        - 400: the volunteer id or username is not provided
        - 404: either the submission or volunteer is not found with the provided IDs

        :param request: the request done to the API
        :param pk: the primary key of the submission, i.e. the submission id
        :return: either a tuple of the submission and volunteer, or an error response
        """
        try:
            submission = Submission.objects.get(id=pk)
        except Submission.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = self.get_volunteer_info_from_json(
            request, error_out_if_bad_data=True
        )
        if isinstance(response, Response):
            return response  # it exploded, return the error
        else:
            volunteer_id = response

        volunteer = self.get_volunteer(volunteer_id=volunteer_id)
        if not volunteer:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return submission, volunteer

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
        ctq = request.query_params.get("ctq", False)
        if ctq:
            delay_time = timezone.now()
        else:
            delay_time = timezone.now() - timedelta(hours=settings.ARCHIVIST_DELAY_TIME)
        queryset = Submission.objects.filter(
            Q(completed_by=None)
            & Q(claimed_by=None)
            & Q(create_time__lt=delay_time)
            & Q(archived=False)
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
    @action(detail=True, methods=["post"])
    def unclaim(self, request: Request, pk: int) -> Response:
        """
        Unclaim the specified submission, from the specified volunteer.

        The volunteer is specified in the HTTP body.
        """
        response = self._get_possible_claim_done_errors(request, pk)
        if isinstance(response, Response):
            # Something went wrong, return the error
            return response
        else:
            submission, volunteer = response

        if submission.claimed_by is None:
            return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        if submission.claimed_by != volunteer:
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
    @action(detail=True, methods=["post"])
    def claim(self, request: Request, pk: int) -> Response:
        """
        Claim the specified submission from the specified volunteer.

        The volunteer is specified in the HTTP body.
        """
        response = self._get_possible_claim_done_errors(request, pk)
        if isinstance(response, Response):
            # Something went wrong, return the error
            return response
        else:
            submission, volunteer = response

        if submission.claimed_by is not None:
            return Response(status=status.HTTP_409_CONFLICT)

        submission.claimed_by = volunteer
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
    @action(detail=True, methods=["post"])
    def done(self, request: Request, pk: int) -> Response:
        """
        Mark the submission as done from the specified volunteer.

        When "mod_override" is provided as a field in the HTTP body and is true,
        and the requesting user is a mod, then the check of whether the
        completing volunteer is the volunteer that claimed the submission is
        skipped.

        Note that this API call has a certain chance to send a message to
        Slack for the random check of this transcription.
        """
        response = self._get_possible_claim_done_errors(request, pk)
        if isinstance(response, Response):
            # Something went wrong, return the error
            return response
        else:
            submission, volunteer = response

        if submission.completed_by is not None:
            return Response(status=status.HTTP_409_CONFLICT)

        if submission.claimed_by is None:
            return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        mod_override = (
            request.data.get("mod_override", False) and request.user.is_grafeas_staff
        )

        if not mod_override:
            if submission.claimed_by != volunteer:
                return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        submission.completed_by = volunteer
        submission.complete_time = timezone.now()
        submission.save()

        if self._should_check_transcription(volunteer):
            transcription = Transcription.objects.filter(submission=submission)
            url = transcription.first().url if transcription else submission.tor_url
            slack.chat_postMessage(
                channel="#transcription_check",
                text="Please check the following transcription of "
                f"u/{volunteer.username}: {url}.",
            )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
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
            404: "Source requested was not found."
        },
    )
    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """
        Create a new submission.

        Note that both the original id and the source id should be supplied.
        """
        original_id = request.data.get("original_id")
        source = request.data.get("source")

        if not original_id or not source:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if (source_obj := Source.objects.filter(pk=source).first()) is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        url = request.data.get("url")
        tor_url = request.data.get("tor_url")

        submission = Submission.objects.create(
            original_id=original_id, source=source_obj, url=url, tor_url=tor_url
        )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )


class TranscriptionViewSet(viewsets.ModelViewSet, VolunteerMixin):
    """The API view to view and edit information regarding Transcribers."""

    queryset = Transcription.objects.all().order_by("-post_time")
    serializer_class = TranscriptionSerializer
    permission_classes = (AdminApiKeyCustomCheck,)

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            required=[
                "submission_id"
                "original_id",
                "username",
                "source",
                "t_url",
                "t_text",
            ],
            properties={
                "submission_id": Schema(type="string"),
                "username": Schema(type="string"),
                "original_id": Schema(type="string"),
                "completion_method": Schema(type="string"),
                "t_url": Schema(type="string"),
                "t_text": Schema(type="string"),
            },
        ),
        responses={
            201: DocResponse(
                "Successful transcription creation", schema=serializer_class
            ),
            400: "The request does not adhere to the specified HTTP body",
            404: "Either the specified submission or volunteer is not found",
        },
    )
    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        """
        Create a new transcription.

        The following fields are passed in the HTTP Body:
            - submission_id         the ID of the corresponding submission
            - v_id (or username)    the ID or username of the authoring volunteer
            - original_id           the base36 ID of the comment
            - source                the system which has submitted this request
            - t_url                 the direct url to the transcription
            - t_text                the text of the transcription
            - ocr_text              the text of tor_ocr

        Note that instead of the username, the "v_id" property to supply the
        volunteer can also be used to create a transcription.
        """
        original_id = request.data.get("submission_id")
        if original_id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # did they give us an actual submission id?
        submission = Submission.objects.filter(original_id=original_id).first()
        if not submission:
            # ...or did they give us the database ID of a submission?
            submission = Submission.objects.filter(id=original_id).first()
            if not submission:
                return Response(status=status.HTTP_404_NOT_FOUND)

        volunteer = self.get_volunteer_from_request(request)
        if not volunteer:
            return Response(status=status.HTTP_404_NOT_FOUND)

        original_id = request.data.get("original_id")
        if not original_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        source = request.data.get("source")
        if not source:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        source = Source.objects.get(name=source)

        url = request.data.get("t_url")
        if not url:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        transcription_text = request.data.get("t_text")
        if not transcription_text:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        removed_from_reddit = request.data.get("removed_from_reddit", False)

        transcription = Transcription.objects.create(
            submission=submission,
            author=volunteer,
            original_id=original_id,
            url=url,
            source=source,
            text=transcription_text,
            removed_from_reddit=removed_from_reddit,
        )
        return Response(
            data=self.serializer_class(
                transcription, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        manual_parameters=[Parameter("original_id", "query", type="string")],
        responses={400: 'Query parameter "original_id" not present'},
    )
    @action(detail=False, methods=["get"])
    def search(self, request: Request, *args: object, **kwargs: object) -> Response:
        """
        Search for the transcriptions of a specific submission.

        Note that providing a original_id as a query parameter is mandatory.
        """
        original_id = request.query_params.get("original_id", None)

        if not original_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        queryset = Transcription.objects.filter(submission__original_id=original_id)
        return Response(
            data=self.serializer_class(
                queryset, many=True, context={"request": request}
            ).data
        )

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
