"""Views that specifically relate to volunteers."""
import uuid

from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.authentication import BlossomApiPermission
from api.helpers import validate_request
from api.models import Source, Submission, Transcription
from api.serializers import VolunteerSerializer
from authentication.models import BlossomUser


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

    queryset = BlossomUser.objects.filter(is_volunteer=True).order_by("date_joined")
    serializer_class = VolunteerSerializer
    basename = "volunteer"
    permission_classes = (BlossomApiPermission,)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["id", "username", "is_volunteer", "accepted_coc", "blacklisted"]

    @csrf_exempt
    @swagger_auto_schema(
        manual_parameters=[Parameter("username", "query", type="string")],
        responses={
            400: 'No "username" as a query parameter.',
            404: "No volunteer with the specified username.",
        },
    )
    @action(detail=False, methods=["get"])
    @validate_request(query_params={"username"})
    def summary(self, request: Request, username: str = None) -> Response:
        """Get information on the volunteer with the provided username."""
        user = get_object_or_404(BlossomUser, username=username, is_volunteer=True)
        return Response(self.serializer_class(user).data)

    @swagger_auto_schema(responses={404: "No volunteer with the specified ID."},)
    @action(detail=True, methods=["get"])
    def rate(self, request: Request, pk: int) -> JsonResponse:
        """Get the number of transcriptions the volunteer made per UTC day.

        IMPORTANT: To reduce the number of entries, this does not
        include days on which the user did not make any transcriptions!
        """
        user = get_object_or_404(BlossomUser, id=pk, is_volunteer=True)

        # https://stackoverflow.com/questions/8746014/django-group-by-date-day-month-year
        rate = (
            Transcription.objects.filter(author=user)
            .annotate(date=TruncDate("create_time"))
            .values("date")
            .annotate(count=Count("id"))
            .values("date", "count")
            .order_by("date")
        )
        per_page = request.GET.get("per_page", 50)
        page_number = request.GET.get("page", 1)
        paginator = Paginator(rate, per_page)
        page_obj = paginator.get_page(page_number)
        return JsonResponse(
            {
                "page_num": page_obj.number,
                "data": list(page_obj.object_list),
                "total_pages": page_obj.paginator.num_pages,
            }
        )

    @csrf_exempt
    @swagger_auto_schema(
        request_body=no_body, responses={404: "No volunteer with the specified ID."}
    )
    @action(detail=True, methods=["patch"])
    def gamma_plusone(self, request: Request, pk: int) -> Response:
        """
        Add one gamma through a fake completed transcription by the volunteer.

        This method should only be called in the case of erroneous behavior of
        the proper procedure of awarding gamma.
        """
        user = get_object_or_404(BlossomUser, id=pk)

        gamma_plus_one, _ = Source.objects.get_or_create(name="gamma_plus_one")

        dummy_post = Submission.objects.create(source=gamma_plus_one, completed_by=user)
        Transcription.objects.create(
            submission=dummy_post,
            author=user,
            original_id=str(uuid.uuid4()),
            source=gamma_plus_one,
            text="dummy transcription",
        )
        return Response(self.serializer_class(user).data)

    @csrf_exempt
    @swagger_auto_schema(
        request_body=Schema(
            type="object", properties={"username": Schema(type="string")}
        ),
        responses={
            201: DocResponse("User successfully updated.", schema=serializer_class),
            400: 'No "username" key in the data body.',
            422: "There already exists a volunteer with the specified username.",
        },
    )
    @validate_request(data_params={"username"})
    def create(
        self, request: Request, username: str = None, *args: object, **kwargs: object
    ) -> Response:
        """Create a new user with the specified username."""
        if BlossomUser.objects.filter(username=username).exists():
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        user = BlossomUser.objects.create(username=username)
        user.set_unusable_password()

        return Response(
            self.serializer_class(user).data, status=status.HTTP_201_CREATED
        )

    @csrf_exempt
    @swagger_auto_schema(
        request_body=no_body,
        responses={
            200: "The volunteer has been updated successfully.",
            404: "No volunteer with the specified username.",
            409: "The volunteer has already accepted the Code of Conduct.",
        },
    )
    @validate_request(query_params={"username"})
    @action(detail=False, methods=["post"])
    def accept_coc(self, request: Request, username: str) -> Response:
        """Set the requested volunteer as having accepted the Code of Conduct."""
        user = get_object_or_404(BlossomUser, username=username, is_volunteer=True)
        if user.accepted_coc is True:
            return Response(status=status.HTTP_409_CONFLICT)
        user.accepted_coc = True
        user.save()
        return Response(status=status.HTTP_200_OK)
