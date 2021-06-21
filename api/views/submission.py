"""Views that specifically relate to submissions."""
import random
from datetime import timedelta
from typing import Union

from django.conf import settings
from django.db.models.functions import Length
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from slack import WebClient

from api.authentication import BlossomApiPermission
from api.helpers import validate_request
from api.models import Source, Submission, Transcription
from api.serializers import SubmissionSerializer
from api.views.slack_helpers import client as slack
from authentication.models import BlossomUser


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
    permission_classes = (BlossomApiPermission,)
    queryset = Submission.objects.order_by("id")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "id",
        "original_id",
        "claimed_by",
        "completed_by",
        "source",
        "url",
        "tor_url",
        "archived",
        "content_url",
        "redis_id",
    ]

    @swagger_auto_schema(
        manual_parameters=[
            Parameter("ctq", "query", type="boolean"),
            Parameter("hours", "query", type="integer"),
        ],
        required=["source"],
        responses={
            200: DocResponse("Successful operation", schema=serializer_class),
            400: "The custom hour provided is invalid.",
        },
    )
    @validate_request(query_params={"source"})
    @action(detail=False, methods=["get"])
    def expired(self, request: Request, source: str = None) -> Response:
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
            hours = request.query_params.get("hours", settings.ARCHIVIST_DELAY_TIME)
            try:
                hours = int(hours)
                delay_time = timezone.now() - timedelta(hours=hours)
            except ValueError:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        source_obj = get_object_or_404(Source, pk=source)
        queryset = Submission.objects.filter(
            completed_by=None,
            claimed_by=None,
            create_time__lt=delay_time,
            archived=False,
            source=source_obj,
            removed_from_queue=False,
        )
        return Response(self.get_serializer(queryset[:100], many=True).data)

    @swagger_auto_schema(
        manual_parameters=[Parameter("hours", "query", type="integer")],
        required=["source"],
        responses={
            200: DocResponse("Successful operation", schema=serializer_class),
            400: "The hour provided is invalid.",
        },
    )
    @validate_request(query_params={"source"})
    @action(detail=False, methods=["get"])
    def in_progress(self, request: Request, source: str = None) -> Response:
        """
        Return all old submissions that are still in progress.

        Sometimes submissions get lost in the ether because volunteers forget
        to complete them. This function accepts a query string of `hours` that
        can be used to adjust the amount of time that is considered before returning
        a submission that is still in progress. Default is four hours.
        """
        hours = request.query_params.get("hours", 4)
        try:
            hours = int(hours)
            delay_time = timezone.now() - timedelta(hours=hours)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        source_obj = get_object_or_404(Source, pk=source)
        queryset = Submission.objects.filter(
            completed_by=None,
            claimed_by__isnull=False,
            claim_time__lt=delay_time,
            archived=False,
            source=source_obj,
            removed_from_queue=False,
        )
        return Response(self.get_serializer(queryset[:100], many=True).data)

    @swagger_auto_schema(
        responses={200: DocResponse("Successful operation", schema=serializer_class)},
        required=["source"],
    )
    @validate_request(query_params={"source"})
    @action(detail=False, methods=["get"])
    def unarchived(self, request: Request, source: str = None) -> Response:
        """
        Return all completed old submissions which are not archived.

        The definition of old in this method is half an hour. When no posts are
        found, an empty array is returned in the body.
        """
        source_obj = get_object_or_404(Source, pk=source)
        delay_time = timezone.now() - timedelta(
            hours=settings.ARCHIVIST_COMPLETED_DELAY_TIME
        )
        queryset = Submission.objects.filter(
            completed_by__isnull=False,
            complete_time__lt=delay_time,
            archived=False,
            source=source_obj,
        )
        return Response(data=self.get_serializer(queryset[:100], many=True).data)

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
            423: "The user is blacklisted",
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

        if user.blacklisted:
            return Response(status=status.HTTP_423_LOCKED)

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
            403: "The volunteer has not accepted the Code of Conduct",
            404: "The specified volunteer or submission is not found",
            409: "The submission is already claimed",
            423: "The user is blacklisted",
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

        if user.blacklisted:
            return Response(status=status.HTTP_423_LOCKED)

        if not user.accepted_coc:
            return Response(status=status.HTTP_403_FORBIDDEN)

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
        for the check is provided. For example, if the probability listed is
        (5, 1), then for the first five transcriptions there is a 100% probability
        that their transcription will be posted to the channel. If the probability
        listed reads something like (100, 0.2), then there is a 1 in 5 chance
        (20%) of their transcription being posted. The chance will get lower as
        the volunteer gains more experience, as the entire point of this system
        is to verify that they are continuing to do a good job, not to constantly
        be looking over their shoulder.

        :param volunteer:   the volunteer for which the post should be checked
        :return:            whether the post should be checked
        """
        probabilities = [
            (5, 1),
            (50, 0.4),
            (100, 0.2),
            (250, 0.1),
            (500, 0.05),
            (1000, 0.02),
            (5000, 0.01),
        ]
        for (gamma, probability) in probabilities:
            if volunteer.gamma <= gamma:
                if random.random() < probability:
                    return True
                else:
                    return False
        return random.random() < 0.005

    def _send_transcription_to_slack(
        self,
        transcription: Transcription,
        submission: Submission,
        user: BlossomUser,
        slack: WebClient,
    ) -> None:
        """Notify slack for the transcription check."""
        url = None
        # it's possible that we either won't pull a transcription object OR that
        # a transcription object won't have a URL. If either fails, then we default
        # to the submission's URL.
        if transcription:
            url = transcription.url
        if not url:
            url = submission.tor_url

        url = "https://reddit.com" + url if submission.source == "reddit" else url

        msg = (
            f"Please check the following transcription of " f"u/{user.username}: {url}."
        )

        # the `done` process is still going here, so they technically don't have
        # a transcription yet. It's about to get assigned, but for right now the
        # value is still zero.
        if user.gamma == 0:
            msg = ":rotating_light: First transcription! :rotating_light: " + msg

        slack.chat_postMessage(
            channel="#transcription_check", text=msg,
        )

    def _check_for_rank_up(
        self, user: BlossomUser, submission: Submission = None
    ) -> None:
        """
        Check if a volunteer has changed rank and, if so, notify Slack.

        Because gamma is calculated off of transcriptions and the `done` endpoint
        is called after the transcription is posted, by the time that we go to
        calculate the gamma of the user, their gamma has already changed... so
        we'll just subtract one from their current score and see if that changes
        anything.
        """
        current_rank = user.get_rank()
        if user.get_rank(override=user.gamma - 1) != current_rank:
            slack.chat_postMessage(
                channel="#new_volunteers_meta",
                text=(
                    f"Congrats to {user.username} on achieving the rank"
                    f" of {current_rank}!! {submission.tor_url}"
                ),
            )

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
            403: "The volunteer has not accepted the Code of Conduct",
            404: "The specified volunteer or submission is not found",
            409: "The submission is already completed",
            412: "The submission is not claimed or claimed by someone else",
            423: "The user is blacklisted",
            428: "A transcription belonging to the volunteer was not found",
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

        if user.blacklisted:
            return Response(status=status.HTTP_423_LOCKED)

        if not user.accepted_coc:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if submission.completed_by is not None:
            return Response(status=status.HTTP_409_CONFLICT)

        if submission.claimed_by is None:
            return Response(status=status.HTTP_412_PRECONDITION_FAILED)

        mod_override = (
            request.data.get("mod_override", "False") == "True"
            and request.user.is_grafeas_staff
        )

        if not mod_override:
            if submission.claimed_by != user:
                return Response(status=status.HTTP_412_PRECONDITION_FAILED)
            transcription = Transcription.objects.filter(submission=submission).first()
            if not transcription:
                return Response(status=status.HTTP_428_PRECONDITION_REQUIRED)

            if self._should_check_transcription(user):
                self._send_transcription_to_slack(
                    transcription, submission, user, slack
                )

        submission.completed_by = user
        submission.complete_time = timezone.now()
        submission.save()

        self._check_for_rank_up(user, submission)

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            required=["original_id", "source", "content_url"],
            properties={
                "original_id": Schema(type="string"),
                "source": Schema(type="string"),
                "url": Schema(type="string"),
                "tor_url": Schema(type="string"),
                "content_url": Schema(type="string"),
                "cannot_ocr": Schema(type="boolean"),
            },
        ),
        responses={
            201: DocResponse("Successful creation", schema=serializer_class),
            400: "Required parameters not provided",
            404: "Source requested was not found",
        },
    )
    @validate_request(data_params={"original_id", "source", "content_url"})
    def create(
        self,
        request: Request,
        original_id: str = None,
        source: str = None,
        content_url: str = None,
        cannot_ocr: bool = None,
        *args: object,
        **kwargs: object,
    ) -> Response:
        """
        Create a new submission.

        Note that both the original id, source, and content_url should be supplied.
        """
        source_obj = get_object_or_404(Source, pk=source)
        url = request.data.get("url")
        tor_url = request.data.get("tor_url")
        # allows pre-marking submissions we know won't be able to make it through OCR
        cannot_ocr = request.data.get("cannot_ocr", "False") == "True"
        submission = Submission.objects.create(
            original_id=original_id,
            source=source_obj,
            url=url,
            tor_url=tor_url,
            content_url=content_url,
            cannot_ocr=cannot_ocr,
        )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    def _get_limit_value(self, request: Request, default: int = 10) -> Union[int, None]:
        """
        Retrieve an optional limit parameter for get_transcribot_queue.

        If no limit is passed in, a default of 10 is used. Passing in "none"
        will return the entire queryset.
        """
        limit_value = request.query_params.get("limit")
        if not limit_value:
            return default
        try:
            return int(limit_value)
        except (ValueError, TypeError):
            if str(limit_value).lower() == "none":
                return None
            else:
                return default

    @swagger_auto_schema(
        responses={
            200: DocResponse("Successful operation", schema=serializer_class),
            400: "Required parameters not provided",
        }
    )
    @validate_request(query_params={"source"})
    @action(detail=False, methods=["get"])
    def get_transcribot_queue(
        self, request: Request, source: str = None
    ) -> JsonResponse:
        """
        Get the submissions that still need to be attempted by transcribot.

        The helper method of `.has_ocr_transcription` exists, but you cannot
        filter a django queryset on a property because it's generated in Python,
        not stored in the database.

        All transcriptions that have text but are missing vital information (like
        the original_id) because this information will be added by transcribot
        when the transcription is posted. This endpoint will return all the
        submissions that need updates along with their transcription FKs, then
        transcribot pulls the transcription text as needed.

        Brief walkthrough of this query:

        Grab all submissions that:
        * are from a given source
        * have a transcription object written by transcribot
        * that the transcription objects do NOT have an original_id key
          - if that key was there, that would mean that the transcription
            had been posted
        * that the submission has not been marked as removed from the queue
          - ie. it broke rules and was reported & removed
        """
        source_obj = get_object_or_404(Source, pk=source)
        transcribot = BlossomUser.objects.get(username="transcribot")
        return_limit = self._get_limit_value(request)
        queryset = Submission.objects.filter(
            source=source_obj,
            transcription__author=transcribot,
            transcription__original_id__isnull=True,
            removed_from_queue=False,
            cannot_ocr=False,
        ).values("id", "tor_url", "transcription__id", "transcription__text")[
            :return_limit
        ]
        return JsonResponse({"data": list(queryset)})
        # return Response(
        #     data=self.get_serializer(queryset[:return_limit], many=True).data
        # )

    @swagger_auto_schema(
        request_body=Schema(
            type="object",
            required=["username"],
            properties={"username": Schema(type="string"), "count": Schema(type="int")},
        ),
        responses={
            200: DocResponse(
                "Submissions were successfully yeeted", schema=serializer_class
            ),
            400: "Required parameters not provided",
            411: "No yeetable submissions were found",
        },
    )
    @validate_request(data_params={"username"})
    @action(detail=False, methods=["post"])
    def yeet(self, request: Request, username: str = None) -> Response:
        """
        Manually fix users who have too many auto-generated submissions.

        For an unidentified reason, sometimes the bootstrap script is creating
        too many submissions for a given user. This function allows us to yeet
        some of the offending submissions out of the database while we focus on
        cleaning and maintaining the data with the redis cache after deployment.
        """
        user = get_object_or_404(BlossomUser, username=username)
        count = int(request.data.get("count", 1))
        auto_generated_submissions = (
            Submission.objects.filter(completed_by=user)
            .annotate(id_len=Length("original_id"))
            .filter(id_len__gt=10)
        )

        if auto_generated_submissions.count() == 0:
            return Response(status=status.HTTP_411_LENGTH_REQUIRED)
        qs = Submission.objects.filter(
            pk__in=auto_generated_submissions.values_list("pk", flat=True)[:count]
        )
        yeeted = qs.count()
        qs.delete()

        return Response(status=status.HTTP_200_OK, data={"total_yeeted": yeeted})

    @action(detail=False, methods=["post"])
    def bulkcheck(self, request: Request) -> Response:
        """Start with of a list of IDs, then return which ones are new to us."""
        # we can't do a filter for things that don't exist, and excluding doesn't
        # make sense here because we're looking for IDs that actually don't exist.
        urls = dict(request.data).get("urls")
        submissions = Submission.objects.filter(url__in=urls)
        for submission in submissions:
            if submission.url in urls:
                urls.pop(urls.index(submission.url))

        return Response(status=status.HTTP_200_OK, data=urls)
