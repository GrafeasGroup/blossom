import uuid
import random
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter, Response as DocResponse, Schema
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import Tuple

from blossom.api import Summary
from blossom.api.authentication import AdminApiKeyCustomCheck
from blossom.api.helpers import (
    VolunteerMixin, RequestDataMixin, ERROR, SUCCESS, build_response
)
from blossom.api.models import Submission, Transcription
from blossom.api.serializers import (
    VolunteerSerializer,
    SubmissionSerializer,
    TranscriptionSerializer,
)
from blossom.authentication.models import BlossomUser
from blossom.slack_conn.helpers import client as slack


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_summary="Get information on all volunteers or a specific"
                          " volunteer if specified.",
        operation_description="Include the username as a query to filter"
                              " the volunteers on the specified username.",
        manual_parameters=[
            Parameter(
                "username",
                "query",
                type="string"
            )
        ]
    )
)
class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = BlossomUser.objects.filter(is_volunteer=True).order_by("-join_date")
    serializer_class = VolunteerSerializer
    basename = "volunteer"
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self):
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
        manual_parameters=[
            Parameter(
                "username",
                "query",
                type="string"
            )
        ],
        responses={
            400: "No \"username\" as a query parameter.",
            404: "No volunteer with the specified username."
        }
    )
    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """
        Get information on the volunteer with the provided username.
        """
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
        request_body=no_body,
        responses={
            404: "No volunteer with the specified ID."
        }
    )
    @action(detail=True, methods=["patch"])
    def gamma_plusone(self, request: Request, pk: int) -> Response:
        """
        Add one gamma through creating a fake completed transcription in the
        respective volunteer's name.

        This method should only be called in the case of erroneous behavior of
        the proper procedure of awarding gamma.
        """
        try:
            volunteer = BlossomUser.objects.get(id=pk)
        except BlossomUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        dummy_post = Submission.objects.create(
            source="gamma_plus_one",
            completed_by=volunteer
        )
        Transcription.objects.create(
            submission=dummy_post,
            author=volunteer,
            transcription_id=str(uuid.uuid4()),
            completion_method="gamma_plus_one",
            text="dummy transcription"
        )
        return Response(self.serializer_class(volunteer).data)

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse(
                "Successful creation",
                schema=serializer_class),
            400: "No \"username\" key in the data body",
            422: "There already exists a volunteer with the specified username"
        }
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Create a new user with the specified username.
        """
        username = request.data.get("username")

        if not username:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if BlossomUser.objects.filter(username=username).first():
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        volunteer = BlossomUser.objects.create(username=username)
        volunteer.set_unusable_password()

        return Response(
            self.serializer_class(volunteer).data,
            status=status.HTTP_201_CREATED
        )


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_summary="Get information on all submissions or a specific"
                          " submission if specified.",
        operation_description="Include the submission_id as a query to filter"
                              " the submissions on the specified ID.",
        manual_parameters=[
            Parameter(
                "submission_id",
                "query",
                type="string"
            )
        ]
    )
)
class SubmissionViewSet(viewsets.ModelViewSet, RequestDataMixin, VolunteerMixin):
    queryset = Submission.objects.all().order_by("-post_time")
    serializer_class = SubmissionSerializer
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self):
        """
        Get information on all submissions or a specific submission if specified.

        When a submission_id is provided as a query parameter, filter the
        queryset on that submission.
        """
        queryset = Submission.objects.all().order_by("id")
        submission_id = self.request.query_params.get("submission_id", None)
        if submission_id is not None:
            queryset = queryset.filter(submission_id=submission_id)
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
            request,
            error_out_if_bad_data=True
        )
        if isinstance(response, Response):
            return response  # it exploded, return the error
        else:
            volunteer_id = response

        volunteer = self.get_volunteer(id=volunteer_id)
        if not volunteer:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return submission, volunteer

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                "ctq",
                "query",
                type="boolean"
            )
        ],
        responses={
            200: DocResponse(
                "Successful operation",
                schema=serializer_class
            )
        }
    )
    @action(detail=False, methods=["get"])
    def expired(self, request: Request) -> Response:
        """
        Return all submissions that are older than 18 hours and have not
        been claimed or completed yet.

        If the query string of ctq is passed in with a value of True then
        return all posts that have not been completed or claimed.

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
            & Q(submission_time__lt=delay_time)
            & Q(archived=False)
        )
        return Response(
            self.get_serializer(
                queryset,
                many=True,
                context={"request", request}).data
        )

    @swagger_auto_schema(
        responses={
            200: DocResponse(
                "Successful operation",
                schema=serializer_class
            )
        }
    )
    @action(detail=False, methods=["get"])
    def unarchived(self, request: Request) -> Response:
        """
        Return all submissions that are older than a set number of hours,
        have been completed by someone, and are not yet archived.

        When no posts are found, an empty array is returned in the body.
        """
        delay_time = timezone.now() - timedelta(
            hours=settings.ARCHIVIST_COMPLETED_DELAY_TIME
        )
        queryset = Submission.objects.filter(
            ~Q(completed_by=None)
            & Q(complete_time__lt=delay_time)
            & Q(archived=False)
        )
        return Response(data=self.get_serializer(queryset, many=True).data)

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse(
                "Successful unclaim operation",
                schema=serializer_class
            ),
            400: "The volunteer username is not provided",
            404: "The specified volunteer or submission is not found",
            406: "The specified volunteer has not claimed the specified submission",
            409: "The submission has already been completed",
            412: "The submission has not yet been claimed"
        }
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
            data=self.serializer_class(
                submission,
                context={"request": request}
            ).data
        )

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse(
                "Successful claim operation",
                schema=serializer_class
            ),
            400: "The volunteer username is not provided",
            404: "The specified volunteer or submission is not found",
            409: "The submission is already claimed"
        }
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
            data=self.serializer_class(
                submission,
                context={"request": request}
            ).data
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
            (5000, 0.1)
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
                "mod_override": Schema(type="boolean")
            }
        ),
        responses={
            201: DocResponse(
                "Successful done operation",
                schema=serializer_class
            ),
            400: "The volunteer username is not provided",
            404: "The specified volunteer or submission is not found",
            409: "The submission is already completed",
            412: "The submission is not claimed or claimed by someone else"
        }
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

        mod_override = request.data.get("mod_override", False) \
                       and request.user.is_grafeas_staff

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
                     f"u/{volunteer.username}: {url}."
            )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(
                submission,
                context={"request": request}
            ).data
        )

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            properties={
                "submission_id": Schema(type="string"),
                "source": Schema(type="string"),
                "url": Schema(type="string"),
                "tor_url": Schema(type="string")
            }
        ),
        responses={
            201: DocResponse(
                "Successful creation",
                schema=serializer_class
            ),
            400: "Required parameters not provided"
        }
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Create a new submission.

        Note that both the submission id and the source should be supplied.
        """
        submission_id = request.data.get("submission_id")
        source = request.data.get("source")

        url = request.data.get("url")
        tor_url = request.data.get("tor_url")

        if not submission_id or not source:
            Response(status=status.HTTP_400_BAD_REQUEST)
            return build_response(
                ERROR,
                "Must contain the keys `submission_id` (str, 20char max) and "
                "`source` (str 20char max)",
                status.HTTP_400_BAD_REQUEST,
            )

        submission = Submission.objects.create(
            submission_id=submission_id, source=source, url=url, tor_url=tor_url
        )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(
                submission,
                context={"request": request}
            ).data
        )


class TranscriptionViewSet(viewsets.ModelViewSet, VolunteerMixin):
    queryset = Transcription.objects.all().order_by("-post_time")
    serializer_class = TranscriptionSerializer
    permission_classes = (AdminApiKeyCustomCheck,)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Required fields:

            submission_id         | str, the post on r/ToR
            v_id (or username)    | str, volunteer ID in Blossom
            t_id                  | str, base36 transcription comment ID
            completion_method     | str, whatever system submitted this object
            t_url                 | str, direct url for the transcription
            ---
            t_text                | str  OR
            ocr_text              | str

        Optional fields:

            removed_from_reddit   | bool

        There must be one field that has text on it, either t_text or ocr_text.
        t_text is used for submitting human-generated text from a volunteer
        and ocr_text is used for submitting text from tor_ocr.

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        submission_id = request.data.get("submission_id")
        if submission_id is None:
            return build_response(
                ERROR,
                "Missing data body key `submission_id`, str; the ID of "
                "the post the transcription is on.",
                status.HTTP_400_BAD_REQUEST,
            )

        # did they give us an actual submission id?
        p = Submission.objects.filter(submission_id=submission_id).first()
        if not p:
            # ...or did they give us the database ID of a submission?
            p = Submission.objects.filter(id=submission_id).first()
            if not p:
                return build_response(
                    ERROR,
                    f"No post found with ID {submission_id}!",
                    status.HTTP_404_NOT_FOUND,
                )

        v = self.get_volunteer_from_request(request)
        if not v:
            return build_response(
                ERROR,
                "No volunteer found with that ID / username.",
                status.HTTP_404_NOT_FOUND,
            )

        t_id = request.data.get("t_id")
        if not t_id:
            return build_response(
                ERROR,
                "Missing data body key `t_id`, str; the ID of the transcription.",
                status.HTTP_400_BAD_REQUEST,
            )

        completion_method = request.data.get("completion_method")
        if not completion_method:
            return build_response(
                ERROR,
                "Missing data body key `completion_method`, str;"
                " the service this transcription was completed"
                " through. `app`, `ToR`, etc. 20char max.",
                status.HTTP_400_BAD_REQUEST,
            )

        t_url = request.data.get("t_url")
        if not t_url:
            return build_response(
                ERROR,
                "Missing data body key `t_url`, str; the direct"
                " URL for the transcription. Use string `None` if"
                " no URL is available.",
                status.HTTP_400_BAD_REQUEST,
            )

        ocr_text = request.data.get("ocr_text")
        t_text = request.data.get("t_text")
        if not t_text:
            # missing t_text is okay if we have ocr_text.
            if not ocr_text:
                return build_response(
                    ERROR,
                    "Missing data body key `t_text`, str; the content"
                    " of the transcription.",
                    status.HTTP_400_BAD_REQUEST,
                )

        if t_text and ocr_text:
            return build_response(
                ERROR,
                "Received both t_text and ocr_text -- must be one or"
                " the other.",
                status.HTTP_400_BAD_REQUEST
            )

        removed_from_reddit = request.data.get("removed_from_reddit", False)

        t = Transcription.objects.create(
            submission=p,
            author=v,
            transcription_id=t_id,
            completion_method=completion_method,
            url=t_url,
            text=t_text,
            ocr_text=ocr_text,
            removed_from_reddit=removed_from_reddit,
        )
        return build_response(
            SUCCESS,
            f"Transcription ID {t.id} created on post"
            f" {p.submission_id}, written by {v.username}",
            status.HTTP_200_OK,
            data={"id": t.id}
        )

    @action(detail=False, methods=["get"])
    def search(self, request: Request, *args, **kwargs) -> Response:
        """
        Right now, only supports submission_id.

        Usage: http://api.grafeas.org/transcription/search/?submission_id=3

        submission_id   | str, the r/ToR post ID

        :return:
        """

        s_id = request.query_params.get("submission_id", None)

        if not s_id:
            return build_response(
                ERROR,
                "This endpoint only supports submission_id as the current search"
                " ability.",
                status.HTTP_400_BAD_REQUEST
            )

        queryset = Transcription.objects.filter(submission__submission_id=s_id)
        if queryset:
            serializer = self.get_serializer(queryset, many=True)
            return build_response(
                SUCCESS,
                f"Found the folowing transcriptions for requested ID {s_id}.",
                status.HTTP_200_OK,
                data=serializer.data
            )
        else:
            return build_response(
                SUCCESS,
                f"Did not find any transcriptions for requested ID {s_id}.",
                status.HTTP_200_OK
            )

    @action(detail=False, methods=["get"])
    def review_random(self, request: Request, *args, **kwargs) -> Response:
        """
        Pull a random transcription that was completed in the last hour and return it.
        :return: Transcription obj
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)

        queryset = Transcription.objects.filter(post_time__gte=one_hour_ago)

        # TODO: Add system so that we're not pulling the same one over and over

        if not queryset:
            return build_response(
                SUCCESS,
                "No available transcriptions to review.",
                status_code=status.HTTP_200_OK
            )
        else:
            serializer = self.get_serializer(random.choice(queryset))
            return build_response(
                SUCCESS,
                "Found this post from the last hour that can be reviewed. More in the `data` key!",
                status_code=status.HTTP_200_OK,
                data=serializer.data
            )

class SummaryView(APIView):
    """
    send an unauthenticated request to /api/summary
    """

    permission_classes = (AdminApiKeyCustomCheck,)

    def get(self, request, *args, **kw):
        return Response(Summary().generate_summary(), status=status.HTTP_200_OK)


class PingView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kw):
        return Response({"ping?!": "PONG"}, status=status.HTTP_200_OK)
