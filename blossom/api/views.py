from typing import Tuple

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from blossom.api.helpers import (
    AuthMixin,
    VolunteerMixin,
    RequestDataMixin,
    ERROR,
    SUCCESS
)
from blossom.api.responses import youre_not_an_admin
from blossom.api.serializers import (
    VolunteerSerializer,
    SubmissionSerializer,
    TranscriptionSerializer
)
from blossom.api.models import (
    Submission,
    Transcription,
    Volunteer,
    Summary
)


class VolunteerViewSet(viewsets.ModelViewSet, AuthMixin):
    queryset = Volunteer.objects.all().order_by("-join_date")
    serializer_class = VolunteerSerializer
    basename = "volunteer"

    def get_queryset(self):
        """
        Uses a `username` query string parameter to filter for a
        specific volunteer. For example:

        GET http://localhost:8000/api/volunteer/?username=asdfasdfasdf
        """
        queryset = Volunteer.objects.all().order_by("id")
        username = self.request.query_params.get("username", None)
        if username is not None:
            queryset = queryset.filter(user__username=username)
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
        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin)

        username = self.request.query_params.get("username", None)
        if not username:
            return Response(
                {
                    ERROR: "No username received. Use ?username= in your request."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        v = Volunteer.objects.filter(user__username=username).first()
        if not v:
            return Response(
                {
                    ERROR: "No volunteer found with that username."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {
                SUCCESS: f"User {username} was found. See 'data' key for summary.",
                'data': {
                    'username': v.user.username,
                    'gamma': Transcription.objects.filter(author=v).count(),
                    'join_date': v.join_date,
                    'accepted_coc': v.accepted_coc
                }
            },
            status=status.HTTP_200_OK
        )


    @action(detail=True, methods=["post"])
    def set_gamma(self, request: Request, pk: int = None) -> Response:
        """
        Set a user's gamma count to a specific number. This is for overriding
        the existing count for whatever reason.

        Example URL:

        POST http://localhost:8000/api/volunteer/1/set_gamma

        :param request: Request
        :param pk: the primary key of the user we're modifying
        :return: json, a message or error of the result.
        """

        # TODO: Refactor this to actually affect dummy transcriptions so we
        # TODO: can get away from the integer gamma count

        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin, status=status.HTTP_401_UNAUTHORIZED)

        try:
            v = Volunteer.objects.get(id=pk)
        except Volunteer.DoesNotExist:
            return Response(
                {
                    ERROR: "No volunteer with that ID."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        gamma_count = request.data.get("gamma")
        if gamma_count is None:
            return Response(
                {ERROR: "Must specify `gamma` in json with the new int value."},
                status=status.HTTP_400_BAD_REQUEST
            )

        v.gamma = gamma_count
        v.save()
        return Response(
            {SUCCESS: f"Set gamma for user {v.user.username} to {v.gamma}"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def gamma_plusone(self, request: Request, pk: int) -> Response:
        """
        This endpoint updates the given score of a user by one.

        Example URL:

        POST http://localhost:8000/api/volunteer/1/gamma_plusone

        :param request: the incoming API request.
        :param pk: the primary key of the volunteer we're updating.
        :return: json, an error or success message.
        """
        # TODO: Refactor this to actually affect dummy transcriptions so we
        # TODO: can get away from the integer gamma count
        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin, status=status.HTTP_401_UNAUTHORIZED)

        try:
            v = Volunteer.objects.get(id=pk)
        except Volunteer.DoesNotExist:
            return Response(
                {ERROR: "No volunteer with that ID."},
                status=status.HTTP_404_NOT_FOUND
            )

        v.gamma += 1
        v.save()
        return Response(
            {SUCCESS: f"Updated gamma for {v.user.username} to {v.gamma}."},
            status=status.HTTP_200_OK
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        If this is hit, we assume that there is no user object to link to.

        Example URL:

        POST http://localhost:8000/api/volunteer

        :param request: the rest framework request object
        :param args: *
        :param kwargs: **
        :return: Response
        """
        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin, status=status.HTTP_401_UNAUTHORIZED)

        username = request.data.get("username")

        if not username:
            return Response(
                {ERROR: "Must have the `username` key in JSON body."},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_user = Volunteer.objects.filter(user__username=username).first()
        if existing_user:
            return Response(
                {
                    ERROR: f"There is already a user with the username of"
                    f" `{existing_user.username}`"
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        u = User.objects.create_user(username=username)
        v = Volunteer.objects.create(user=u)

        return Response(
            {SUCCESS: f"Volunteer created with username `{v.user.username}`"},
            status=status.HTTP_200_OK
        )


class SubmissionViewSet(viewsets.ModelViewSet, AuthMixin, RequestDataMixin, VolunteerMixin):
    queryset = Submission.objects.all().order_by("-post_time")
    serializer_class = SubmissionSerializer

    def get_queryset(self):
        """
        Uses a `submission_id` query string parameter to filter for a
        specific post. For example:

        GET http://localhost:8000/api/post/?submission_id=t3_asdfgh
        """
        queryset = Submission.objects.all().order_by("id")
        submission_id = self.request.query_params.get("submission_id", None)
        if submission_id is not None:
            queryset = queryset.filter(submission_id=submission_id)
        return queryset

    def _get_possible_claim_done_errors(
        self, request: Request, pk: int
    ) -> [Tuple[Submission, Volunteer], Response]:

        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin, status=status.HTTP_401_UNAUTHORIZED)

        try:
            p = Submission.objects.get(id=pk)
        except Submission.DoesNotExist:
            return Response(
                {ERROR: "No post with that ID."}, status=status.HTTP_404_NOT_FOUND
            )

        resp = self.get_user_info_from_json(request, error_out_if_bad_data=True)
        if isinstance(resp, Response):
            return resp  # it exploded, return the error
        else:
            v_id = resp

        v = self.get_volunteer(id=v_id)
        if not v:
            return Response(
                {ERROR: "No volunteer with that ID / username."},
                status=status.HTTP_404_NOT_FOUND
            )
        return p, v

    @action(detail=True, methods=["post"])
    def claim(self, request: Request, pk: int) -> Response:

        resp = self._get_possible_claim_done_errors(request, pk)
        if isinstance(resp, Response):
            # Something went wrong, return the error
            return resp
        else:
            p, v = resp

        if p.claimed_by is not None:
            return Response(
                {ERROR: f"Post ID {p.id} has been claimed already by {p.claimed_by}!"},
                status=status.HTTP_409_CONFLICT
            )
        p.claimed_by = v
        p.claim_time = timezone.now()
        p.save()

        return Response(
            {SUCCESS: f"Post {p.submission_id} claimed by {v.user.username}"},
            status=status.HTTP_200_OK
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
            return Response(
                {
                    ERROR: f"Post ID {p.id} has already been completed by {p.completed_by}!"
                },
                status=status.HTTP_409_CONFLICT
            )
        p.completed_by = v
        p.complete_time = timezone.now()
        p.save()

        return Response(
            {SUCCESS: f"Post {p.submission_id} completed by {v.user.username}"},
            status=status.HTTP_200_OK
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Called by making a POST request against /api/post/. Must contain the following
        fields in JSON body:

            submission_id: str
            source: str

        May optionally contain the following params in JSON body:

            url: str
            tor_url: str

        :param request: the Django request object.
        :param args:
        :param kwargs:
        :return: Response object.
        """

        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin, status=status.HTTP_401_UNAUTHORIZED)

        submission_id = request.data.get("submission_id")
        source = request.data.get("source")

        url = request.data.get("url")
        tor_url = request.data.get("tor_url")

        if not submission_id or not source:
            return Response(
                {
                    ERROR: "Must contain the keys `submission_id` (str, 20char max) "
                    "and `source` (str 20char max)"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            p = Submission.objects.create(
                submission_id=submission_id, source=source, url=url, tor_url=tor_url
            )
            return Response(
                {SUCCESS: f"Post object {p.id} created!"},
                status=status.HTTP_200_OK

            )
        except:
            return Response(
                {
                    ERROR: "Something went wrong during the creation of the"
                    " post. Please check your arguments and try again."
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class TranscriptionViewSet(viewsets.ModelViewSet, AuthMixin, VolunteerMixin):
    queryset = Transcription.objects.all().order_by("-post_time")
    serializer_class = TranscriptionSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Required fields:

            submission_id         | str
            v_id (or username)    | str
            t_id                  | str
            completion_method     | str
            t_url                 | str
            t_text                | str

        Optional fields:

            removed_from_reddit   | bool

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not any([self.is_admin_key(request), self.is_admin_user(request)]):
            return Response(youre_not_an_admin)

        submission_id = request.data.get("submission_id")
        if not submission_id:
            return Response(
                {
                    ERROR: "Missing JSON body key `submission_id`, str; the ID of "
                    "the post the transcription is on."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        p = Submission.objects.filter(id=submission_id).first()
        if not p:
            return Response(
                {ERROR: f"No post found with ID {submission_id}!"},
                status=status.HTTP_404_NOT_FOUND
            )

        v = self.get_volunteer_from_request(request)
        if not v:
            return Response(
                {ERROR: "No volunteer found with that ID / username."},
                status=status.HTTP_404_NOT_FOUND
            )

        t_id = request.data.get("t_id")
        if not t_id:
            return Response(
                {
                    ERROR: "Missing JSON body key `t_id`, str; the ID of "
                    "the transcription."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        completion_method = request.data.get("completion_method")
        if not completion_method:
            return Response(
                {
                    ERROR: "Missing JSON body key `completion_method`, str;"
                    " the service this transcription was completed"
                    " through. `app`, `ToR`, etc. 20char max."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        t_url = request.data.get("t_url")
        if not t_url:
            return Response(
                {
                    ERROR: "Missing JSON body key `t_url`, str; the direct"
                    " URL for the transcription. Use string `None` if"
                    " no URL is available."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        t_text = request.data.get("t_text")
        if not t_text:
            return Response(
                {
                    ERROR: "Missing JSON body key `t_text`, str; the content"
                    " of the transcription."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        removed_from_reddit = request.data.get("removed_from_reddit", False)

        t = Transcription.objects.create(
            post=p,
            author=v,
            transcription_id=t_id,
            completion_method=completion_method,
            url=t_url,
            text=t_text,
            removed_from_reddit=removed_from_reddit,
        )
        return Response(
            {
                SUCCESS: f"Transcription ID {t.id} created on post"
                f" {p.submission_id}, written by {v.username}"
            },
            status=status.HTTP_200_OK
        )


class SummaryView(APIView):
    """
    send an unauthenticated request to /api/summary
    """
    def get(self, request, *args, **kw):
        return Response(Summary().generate_summary(), status=status.HTTP_200_OK)
