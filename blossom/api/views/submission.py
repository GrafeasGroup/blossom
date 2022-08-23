"""Views that specifically relate to submissions."""
import datetime
import logging
from datetime import timedelta
from typing import Union

from django.conf import settings
from django.db.models import Count, F
from django.db.models.functions import (
    ExtractHour,
    ExtractIsoWeekDay,
    Length,
    TruncDate,
    TruncDay,
    TruncHour,
    TruncMonth,
    TruncSecond,
    TruncWeek,
    TruncYear,
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
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
from blossom.api.models import Source, Submission, Transcription, TranscriptionCheck
from blossom.api.pagination import StandardResultsSetPagination
from blossom.api.serializers import SubmissionSerializer
from blossom.api.slack import client as slack
from blossom.api.slack.actions import (
    ReportMessageStatus,
    ask_about_removing_post,
    update_submission_report,
)
from blossom.api.slack.transcription_check.messages import send_check_message
from blossom.api.views.volunteer import VolunteerViewSet
from blossom.authentication.models import BlossomUser

# The maximum number of posts a user can claim
# depending on their current gamma score
MAX_CLAIMS = [{"gamma": 0, "claims": 1}, {"gamma": 100, "claims": 2}]
logger = logging.getLogger("blossom.api.views.submission")


def _check_for_rank_up(user: BlossomUser, submission: Submission = None) -> None:
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
        msg = (
            f"Congrats to {user.username} on achieving the rank of {current_rank}!!"
            f" {submission.tor_url}"
        )
        try:
            slack.chat_postMessage(channel=settings.SLACK_RANK_UP_CHANNEL, text=msg)
        except:  # noqa
            logger.warning(f"Cannot post message to slack. Msg: {msg}")
            pass


def _get_limit_value(request: Request, default: int = 10) -> Union[int, None]:
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


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_summary="Get information on all submissions or a specific"
        " submission if specified.",
        operation_description="Include the original_id as a query to filter"
        " the submissions on the specified ID.",
        manual_parameters=[
            Parameter("original_id", "query", type="string"),
            Parameter(
                "from",
                "query",
                type="string",
                description=(
                    "Date to use as the start of the returned values."
                    " Example: from=2021-06-01 will return everything after that date."
                ),
            ),
            Parameter(
                "until",
                "query",
                type="string",
                description=(
                    "Date to use as the end of the returned values. Example:"
                    " until=2021-06-05 will return everything from before that date."
                ),
            ),
        ],
    ),
)
class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = (BlossomApiPermission,)
    queryset = Submission.objects.order_by("id")
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        "id": ["exact"],
        "original_id": ["exact"],
        "claimed_by": ["exact", "isnull"],
        "completed_by": ["exact", "isnull"],
        "create_time": ["gt", "gte", "lte", "lt"],
        "claim_time": ["isnull", "gt", "gte", "lte", "lt"],
        "complete_time": ["isnull", "gt", "gte", "lte", "lt"],
        "source": ["exact"],
        "title": ["exact", "isnull", "icontains"],
        "url": ["exact", "isnull"],
        "tor_url": ["exact", "isnull"],
        "archived": ["exact"],
        "content_url": ["exact", "isnull"],
        "redis_id": ["exact", "isnull"],
        "removed_from_queue": ["exact"],
    }
    ordering_fields = [
        "id",
        "title",
        "create_time",
        "last_update_time",
        "claim_time",
        "complete_time",
    ]

    @csrf_exempt
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

    @csrf_exempt
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

    @csrf_exempt
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
        operation_summary=(
            "Retrieve a count of transcriptions for a volunteer per time frame."
        ),
        operation_description=(
            "A paginated endpoint. Pass page_size to control number of results"
            " returned, page to select a different block."
        ),
        manual_parameters=[
            Parameter(
                "time_frame",
                "query",
                type="string",
                enum=["none", "hour", "day", "week", "month", "year"],
                description="The time interval to calculate the rate by. "
                'Must be one of "none", "hour", "day", "week", "month" or "year".'
                'For example, "none" will return the date of every transcription '
                'separately, while "day" will return the daily transcribing rate.',
            ),
            Parameter(
                "utc_offset",
                "query",
                type="number",
                description="The timezone offset to calculate the rate on, in seconds.",
                default=0,
                required=False,
            ),
            Parameter("page_size", "query", type="number"),
            Parameter("page", "query", type="number"),
        ],
    )
    @action(detail=False, methods=["get"])
    def rate(self, request: Request) -> Response:
        """Get the number of transcriptions the volunteer made per time frame.

        IMPORTANT: To reduce the number of entries, this does not
        include days on which the user did not make any transcriptions!
        """
        time_frame = request.GET.get("time_frame", "day")
        utc_offset = int(request.GET.get("utc_offset", "0"))
        # Construct a timezone from the offset
        tzinfo = datetime.timezone(datetime.timedelta(seconds=utc_offset))

        trunc_dict = {
            # Don't group the transcriptions at all
            # TODO: Make this a true noop for transcriptions posted in the same second
            "none": TruncSecond,
            "hour": TruncHour,
            "day": TruncDay,
            # Unfortunately weeks starts on Sunday for this.
            # There doesn't seem to be an ISO week equivalent :(
            "week": TruncWeek,
            "month": TruncMonth,
            "year": TruncYear,
        }

        trunc_fn = trunc_dict.get(time_frame, TruncDate)

        # https://stackoverflow.com/questions/8746014/django-group-by-date-day-month-year
        rate = (
            self.filter_queryset(Submission.objects)
            .filter(complete_time__isnull=False)
            .annotate(date=trunc_fn("complete_time", tzinfo=tzinfo))
            .values("date")
            .annotate(count=Count("id"))
            .values("date", "count")
            .order_by("date")
        )

        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(rate, request)
        return pagination.get_paginated_response(page)

    @csrf_exempt
    @swagger_auto_schema(
        operation_summary=("Get the data to construct a heatmap of the submissions."),
        manual_parameters=[
            Parameter(
                "utc_offset",
                "query",
                type="number",
                description="The timezone offset to calculate the rate on, in seconds.",
                default=0,
                required=False,
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def heatmap(self, request: Request) -> Response:
        """Get the data to generate a heatmap for the volunteer.

        This includes one entry for every weekday and every hour containing the
        number of transcriptions made in that time slot.
        For example, there will be an entry for Sundays at 13:00 UTC, counting
        how many transcriptions the volunteer made in that time.

        The week days are numbered Monday=1 through Sunday=7.
        """
        utc_offset = int(request.GET.get("utc_offset", "0"))
        # Construct a timezone from the offset
        tzinfo = datetime.timezone(datetime.timedelta(seconds=utc_offset))

        heatmap = (
            self.filter_queryset(Submission.objects).filter(complete_time__isnull=False)
            # Extract the day of the week and the hour the transcription was made in
            .annotate(
                day=ExtractIsoWeekDay("complete_time", tzinfo=tzinfo),
                hour=ExtractHour("complete_time", tzinfo=tzinfo),
            )
            # Group by the day and hour
            .values("day", "hour")
            # Count the transcription made in each time slot
            .annotate(count=Count("id"))
            # Return the values
            .values("day", "hour", "count")
            # Order by day first, then hour
            .order_by("day", "hour")
        )

        return Response(heatmap)

    @csrf_exempt
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
            423: "The user is blocked",
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

        if user.blocked:
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

    @csrf_exempt
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
            423: "The user is blocked",
            460: "The volunteer has already claimed too many posts",
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

        if user.blocked:
            return Response(status=status.HTTP_423_LOCKED)

        if not user.accepted_coc:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if submission.claimed_by is not None:
            return Response(
                data=VolunteerViewSet.serializer_class(
                    submission.claimed_by, context={"request": request}
                ).data,
                status=status.HTTP_409_CONFLICT,
            )

        # Determine how many submissions the user has already claimed
        claimed_submissions = Submission.objects.filter(
            claimed_by=user, archived=False, completed_by__isnull=True
        )
        claimed_count = claimed_submissions.count()

        for claim_restriction in reversed(MAX_CLAIMS):
            if user.gamma >= claim_restriction["gamma"]:
                if claimed_count >= claim_restriction["claims"]:
                    # The user has already claimed too many submissions
                    return Response(
                        data=self.get_serializer(
                            claimed_submissions, context={"request": request}, many=True
                        ).data,
                        status=460,
                    )
                break

        submission.claimed_by = user
        submission.claim_time = timezone.now()
        submission.save()

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @csrf_exempt
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
            423: "The user is blocked",
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
        user: BlossomUser = get_object_or_404(BlossomUser, username=username)

        if user.blocked:
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

        transcription = None

        if not mod_override:
            if submission.claimed_by != user:
                return Response(status=status.HTTP_412_PRECONDITION_FAILED)

            transcription = Transcription.objects.filter(
                submission=submission, author=user
            ).first()

            if transcription is None:
                return Response(status=status.HTTP_428_PRECONDITION_REQUIRED)

        # At this point everything looks good, award the user their gamma
        submission.completed_by = user
        submission.complete_time = timezone.now()
        submission.save()

        # Send the transcription to Slack if necessary
        if transcription is not None and user.should_check_transcription():
            # Create a new check object
            check = TranscriptionCheck.objects.create(
                transcription=transcription, trigger=user.transcription_check_reason()
            )
            # Send the check to the check channel
            send_check_message(check)

        # Send rank up message to Slack if necessary
        _check_for_rank_up(user, submission)

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @csrf_exempt
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
                "nsfw": Schema(type="boolean"),
                "title": Schema(type="string"),
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
        nsfw = request.data.get("nsfw", "False") == "True"
        title = request.data.get("title")
        submission = Submission.objects.create(
            original_id=original_id,
            source=source_obj,
            url=url,
            tor_url=tor_url,
            content_url=content_url,
            cannot_ocr=cannot_ocr,
            nsfw=nsfw,
            title=title,
        )

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @csrf_exempt
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
        return_limit = _get_limit_value(request)
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

    @csrf_exempt
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

    @csrf_exempt
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

    @csrf_exempt
    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                "user_id",
                "query",
                type="number",
                description="The user to center the leaderboard on.",
            ),
            Parameter(
                "top_count",
                "query",
                type="number",
                description="The number of users to show from the top leaderboard.",
            ),
            Parameter(
                "above_count",
                "query",
                type="number",
                description="The number of users to show above the given user.",
            ),
            Parameter(
                "below_count",
                "query",
                type="number",
                description="The number of users to show below the given user.",
            ),
        ],
        responses={404: "No volunteer with the specified ID."},
    )
    @action(detail=False, methods=["get"])
    def leaderboard(
        self,
        request: Request,
    ) -> Response:
        """Get the leaderboard for the given user."""
        user_id = request.GET.get("user_id", None)
        if user_id is not None:
            user_id = int(user_id)
        top_count = int(request.GET.get("top_count", 5))
        above_count = int(request.GET.get("above_count", 5))
        below_count = int(request.GET.get("below_count", 5))

        above_data = user_data = below_data = None

        rank_query = (
            # Apply the provided submission filters
            self.filter_queryset(Submission.objects)
            .filter(completed_by__isnull=False)
            # Add author information
            .select_related("completed_by")
            # Group by author
            .values(
                "completed_by", "completed_by__username", "completed_by__date_joined"
            )
            # Count gamma
            .annotate(
                gamma=Count("completed_by"),
                id=F("completed_by"),
                username=F("completed_by__username"),
                date_joined=F("completed_by__date_joined"),
            )
            .values("id", "username", "gamma", "date_joined")
            .order_by(F("gamma").desc(), F("date_joined").desc())
        )
        # TODO: This is very inefficient, maybe there's a better way to do this?
        # Originally we used window expressions to annotate the ranks directly
        # https://stackoverflow.com/questions/54595867/django-model-how-to-add-order-index-annotation
        # Unfortunately that is not supported on all backends
        # Instead, we convert the query into a list and also add the ranks manually
        rank_list = rank_list = [
            {**entry, "rank": i + 1} for i, entry in enumerate(rank_query)
        ]

        # Find the top users
        top_data = rank_list[:top_count]

        if user_id is not None:
            # Find the queried user in the list
            # TODO: Find a more efficient way to do this
            user_index = [user["id"] for user in rank_list].index(user_id)
            user_data = rank_list[user_index]
            # Users with more gamma than the current user
            above_data = rank_list[user_index - 1 - below_count : user_index]
            # Users with less gamma than the current user
            below_data = rank_list[user_index + 1 : user_index + 1 + above_count]

        data = {
            "top": top_data,
            "above": above_data,
            "user": user_data,
            "below": below_data,
        }

        return Response(data)

    @csrf_exempt
    @swagger_auto_schema(
        request_body=Schema(
            type="object", properties={"removed_from_queue": Schema(type="bool")}
        ),
        responses={
            200: DocResponse("Successful removal", schema=serializer_class),
            404: "Submission not found.",
        },
    )
    @action(detail=True, methods=["patch"])
    def remove(self, request: Request, pk: int) -> Response:
        """
        Remove the submission from the queue.

        It is also possible to revert the removal by setting removed_from_queue to false
        in the body of the request.
        """
        submission = get_object_or_404(Submission, id=pk)

        removed_from_queue = request.data.get("removed_from_queue", True)

        submission.removed_from_queue = removed_from_queue
        if removed_from_queue:
            # Revert the approval
            submission.approved = False
        submission.save()

        # Update report message if needed
        if submission.has_slack_report_message:
            update_submission_report(submission, ReportMessageStatus.REMOVED)

        return Response(
            status=status.HTTP_200_OK,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @csrf_exempt
    @swagger_auto_schema(
        request_body=Schema(type="object", properties={"reason": Schema(type="str")}),
        responses={
            201: DocResponse("Successful report", schema=serializer_class),
            404: "Submission not found.",
        },
    )
    @validate_request(data_params={"reason"})
    @action(detail=True, methods=["patch"])
    def report(self, request: Request, pk: int, reason: str) -> Response:
        """Report the given submission.

        This will send a message to the mods to review the submission.
        """
        submission = get_object_or_404(Submission, id=pk)

        if (
            submission.removed_from_queue
            or submission.report_reason is not None
            or submission.approved
        ):
            # The submission is already removed, reported or approved-- ignore the report
            return Response(
                status=status.HTTP_201_CREATED,
                data=self.serializer_class(
                    submission, context={"request": request}
                ).data,
            )

        # Save the report reason
        submission.report_reason = reason
        submission.save(skip_extras=True)

        # Send the report to mod chat
        ask_about_removing_post(submission, reason)

        return Response(
            status=status.HTTP_201_CREATED,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @csrf_exempt
    @swagger_auto_schema(
        request_body=Schema(
            type="object", properties={"approved": Schema(type="bool")}
        ),
        responses={
            200: DocResponse("Successful approval", schema=serializer_class),
            404: "Submission not found.",
        },
    )
    @action(detail=True, methods=["patch"])
    def approve(self, request: Request, pk: int) -> Response:
        """
        Approve the submission.

        This will prevent future reports from being generated for this submission.
        """
        submission = get_object_or_404(Submission, id=pk)

        approved = request.data.get("approved", True)

        submission.approved = approved
        if approved:
            # Revert the removal
            submission.removed_from_queue = False
        submission.save()

        # Update report message if needed
        if submission.has_slack_report_message:
            update_submission_report(submission, ReportMessageStatus.APPROVED)

        return Response(
            status=status.HTTP_200_OK,
            data=self.serializer_class(submission, context={"request": request}).data,
        )

    @csrf_exempt
    @swagger_auto_schema(
        request_body=Schema(type="object", properties={"nsfw": Schema(type="bool")}),
        responses={
            200: DocResponse(
                "Successfully marked as NSFW (or SWF)", schema=serializer_class
            ),
            404: "Submission not found.",
        },
    )
    @action(detail=True, methods=["patch"])
    def nsfw(self, request: Request, pk: int) -> Response:
        """
        Mark a submission as NSFW.

        It is also possible to set it back to SFW by setting nsfw to false
        in the body of the request.
        """
        submission = get_object_or_404(Submission, id=pk)

        nsfw = request.data.get("nsfw", True)

        submission.nsfw = nsfw
        submission.save()
        return Response(
            status=status.HTTP_200_OK,
            data=self.serializer_class(submission, context={"request": request}).data,
        )
