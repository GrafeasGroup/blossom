import uuid
import random
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
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


class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = BlossomUser.objects.filter(is_volunteer=True).order_by("-join_date")
    serializer_class = VolunteerSerializer
    basename = "volunteer"
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self):
        """
        Uses a `username` query string parameter to filter for a
        specific volunteer. For example:

        GET http://api.grafeas.localhost:8000/volunteer/?username=asdfasdfasdf
        """
        queryset = BlossomUser.objects.filter(is_volunteer=True).order_by("id")
        username = self.request.query_params.get("username", None)
        if username is not None:
            queryset = queryset.filter(username=username)
        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """
        Effectively a helper function, just get info on someone and format
        it into a nice little package. Requires the use of ?username= to
        find the appropriate user.

        :param request: Request
        :return: json, a dict that gives relevant information about
            the volunteer.
        """
        username = request.query_params.get("username", None)
        if not username:
            return build_response(
                ERROR,
                "No username received. Use ?username= in your request.",
                status.HTTP_400_BAD_REQUEST,
            )
        v = BlossomUser.objects.filter(
            Q(username=username) & Q(is_volunteer=True)
        ).first()
        if not v:
            return build_response(
                ERROR,
                "No volunteer found with that username.",
                status.HTTP_404_NOT_FOUND,
            )
        return build_response(
            SUCCESS,
            f"User {username} was found. See 'data' key for summary.",
            status.HTTP_200_OK,
            data={
                "username": v.username,
                "gamma": v.gamma,
                "join_date": v.date_joined,
                "accepted_coc": v.accepted_coc,
            },
        )

    @action(detail=True, methods=["post"])
    def gamma_plusone(self, request: Request, pk: int) -> Response:
        def _generate_dummy_post(request):
            return Submission.objects.create(
                source="blossom_gamma_plusone", completed_by=request.user
            )

        def _generate_dummy_transcription(request, post=None):
            if post is None:
                post = _generate_dummy_post(request)
            Transcription.objects.create(
                submission=post,
                author=request.user,
                transcription_id=str(uuid.uuid4()),
                completion_method="blossom_gamma_plusone",
                text="dummy transcription",
            )

        """
        This endpoint updates the given score of a user by one by forcing a
        fake transcription in their name; this should only be used in times
        where the proper methods do not work.

        Example URL:

        POST http://localhost:8000/api/volunteer/1/gamma_plusone

        :param request: the incoming API request.
        :param pk: the primary key of the volunteer we're updating.
        :return: json, an error or success message.
        """
        try:
            v = BlossomUser.objects.get(id=pk)
        except BlossomUser.DoesNotExist:
            return build_response(
                ERROR, "No volunteer with that ID.", status.HTTP_404_NOT_FOUND
            )

        _generate_dummy_transcription(request)

        return build_response(
            SUCCESS, f"Updated gamma for {v.username} to {v.gamma}.", status.HTTP_200_OK
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        If this is hit, we assume that there is no user object to link to.

        Example URL:

        POST http://api.grafeas.localhost:8000/volunteer

        :param request: the rest framework request object
        :param args: *
        :param kwargs: **
        :return: Response
        """
        username = request.data.get("username")

        if not username:
            return build_response(
                ERROR,
                "Must have the `username` key in data body.",
                status.HTTP_400_BAD_REQUEST,
            )

        if existing_user := BlossomUser.objects.filter(username=username).first():
            return build_response(
                ERROR,
                f"There is already a user with the username of"
                f" `{existing_user.username}`.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        v = BlossomUser.objects.create(username=username)
        v.set_unusable_password()

        return build_response(
            SUCCESS,
            f"Volunteer created with username `{v.username}`",
            status.HTTP_200_OK,
        )


class SubmissionViewSet(viewsets.ModelViewSet, RequestDataMixin, VolunteerMixin):
    queryset = Submission.objects.all().order_by("-post_time")
    serializer_class = SubmissionSerializer
    permission_classes = (AdminApiKeyCustomCheck,)

    def get_queryset(self):
        """
        Uses a `submission_id` query string parameter to filter for a
        specific post. For example:

        GET http://api.grafeas.localhost:8000/submission/?submission_id=t3_asdfgh
        """
        queryset = Submission.objects.all().order_by("id")
        submission_id = self.request.query_params.get("submission_id", None)
        if submission_id is not None:
            queryset = queryset.filter(submission_id=submission_id)
        return queryset

    def _get_possible_claim_done_errors(
        self, request: Request, pk: int
    ) -> [Tuple[Submission, BlossomUser], Response]:
        try:
            p = Submission.objects.get(id=pk)
        except Submission.DoesNotExist:
            return build_response(
                ERROR, "No post with that ID.", status.HTTP_404_NOT_FOUND
            )

        resp = self.get_user_info_from_json(request, error_out_if_bad_data=True)
        if isinstance(resp, Response):
            return resp  # it exploded, return the error
        else:
            v_id = resp

        v = self.get_volunteer(id=v_id)
        if not v:
            return build_response(
                ERROR,
                "No volunteer with that ID / username.",
                status.HTTP_404_NOT_FOUND,
            )
        return p, v

    @action(detail=False, methods=["get"])
    def expired(self, request: Request) -> Response:
        """
        Return all submissions that are older than 18 hours and have not
        been claimed or completed yet.

        If the query string of ctq is passed in with a value of True then
        return all posts that have not been completed or claimed.

        :param request:
        :return:
        """
        CTQ = request.query_params.get("ctq", False)
        if CTQ:
            delay_time = timezone.now()
        else:
            delay_time = timezone.now() - timedelta(hours=settings.ARCHIVIST_DELAY_TIME)
        queryset = Submission.objects.filter(
            Q(completed_by=None)
            & Q(claimed_by=None)
            & Q(submission_time__lt=delay_time)
            & Q(archived=False)
        )
        if not queryset:
            return build_response(
                SUCCESS,
                "No available transcriptions to remove.",
                status_code=status.HTTP_200_OK
            )
        else:
            serializer = self.get_serializer(queryset, many=True)
            return build_response(
                SUCCESS,
                "Found the following posts to remove. More in the `data` key!",
                status_code=status.HTTP_200_OK,
                data=serializer.data
            )

    @action(detail=False, methods=["get"])
    def unarchived(self, request: Request) -> Response:
        delay_time = timezone.now() - timedelta(
            hours=settings.ARCHIVIST_COMPLETED_DELAY_TIME
        )
        queryset = Submission.objects.filter(
            ~Q(completed_by=None)
            & Q(complete_time__lt=delay_time)
            & Q(archived=False)
        )
        if not queryset:
            return build_response(
                SUCCESS,
                "No available transcriptions to archive.",
                status_code=status.HTTP_200_OK
            )
        else:
            serializer = self.get_serializer(queryset, many=True)
            return build_response(
                SUCCESS,
                "Found the following posts to archive. More in the `data` key!",
                status_code=status.HTTP_200_OK,
                data=serializer.data
            )

    @action(detail=True, methods=["post"])
    def claim(self, request: Request, pk: int) -> Response:

        resp = self._get_possible_claim_done_errors(request, pk)
        if isinstance(resp, Response):
            # Something went wrong, return the error
            return resp
        else:
            p, v = resp

        if p.claimed_by is not None:
            return build_response(
                ERROR,
                f"Post ID {p.id} has been claimed already by {p.claimed_by}!",
                status.HTTP_409_CONFLICT,
            )

        p.claimed_by = v
        p.claim_time = timezone.now()
        p.save()

        return build_response(
            SUCCESS,
            f"Post {p.submission_id} claimed by {v.username}",
            status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def done(self, request: Request, pk: int) -> Response:
        resp = self._get_possible_claim_done_errors(request, pk)
        if isinstance(resp, Response):
            # Something went wrong, return the error
            return resp
        else:
            p, v = resp

        if p.completed_by is not None:
            return build_response(
                ERROR,
                f"Submission ID {p.submission_id} has already been completed"
                f" by {p.completed_by}!",
                status.HTTP_409_CONFLICT,
            )

        if p.claimed_by is None:
            return build_response(
                ERROR,
                f"Submission ID {p.submission_id} has not yet been claimed!",
                status.HTTP_412_PRECONDITION_FAILED,
            )
        p.completed_by = v
        p.complete_time = timezone.now()
        p.save()

        return build_response(
            SUCCESS,
            f"Submission ID {p.submission_id} completed by {v.username}",
            status.HTTP_200_OK,
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Called by making a POST request against /submission/. Must contain
        the following fields in data body:

            submission_id: str
            source: str

        May optionally contain the following params in data body:

            url: str
            tor_url: str

        :param request: the Django request object.
        :param args:
        :param kwargs:
        :return: Response object.
        """
        submission_id = request.data.get("submission_id")
        source = request.data.get("source")

        url = request.data.get("url")
        tor_url = request.data.get("tor_url")

        if not submission_id or not source:
            return build_response(
                ERROR,
                "Must contain the keys `submission_id` (str, 20char max) and "
                "`source` (str 20char max)",
                status.HTTP_400_BAD_REQUEST,
            )

        p = Submission.objects.create(
            submission_id=submission_id, source=source, url=url, tor_url=tor_url
        )
        return build_response(
            SUCCESS, f"Post object {p.id} created!", status.HTTP_200_OK
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
