from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from blossom.authentication.models import BlossomUser

ERROR = "error"
SUCCESS = "success"


class AuthMixin(object):
    def is_admin_user(self, request: Request) -> bool:
        return any([request.user.is_staff, request.user.is_grafeas_staff])

    def is_admin_key(self, request: Request) -> bool:
        """
        Check the API key that we were passed and see if it belongs to a user.
        If it does, verify that the requested user is an admin. We expect that
        this will only be used in a boolean fashion, but if it finds the user
        then we'll return it in case we need the user later.

        :param request: the api request object
        :return: bool
        """
        token = request.headers.get("X-Api-Key")
        if not token:
            return False

        if request.user.api_key.is_valid(token) and request.user.is_grafeas_staff:
            return True
        else:
            return False


class VolunteerMixin(object):
    def get_volunteer(self, id: int = None, username: str = None) -> [BlossomUser, None]:
        if id:
            return BlossomUser.objects.filter(id=id).first()
        if username:
            return BlossomUser.objects.filter(username=username).first()
        return None

    def get_volunteer_from_request(self, request: Request) -> [None, BlossomUser]:
        v_id = request.data.get("v_id")
        username = request.data.get("username")

        return self.get_volunteer(id=v_id, username=username)


class RequestDataMixin(object):
    def get_user_info_from_json(
        self, request, error_out_if_bad_data=False
    ) -> [None, int, Response]:
        v_id = request.data.get("v_id")
        v_username = request.data.get("v_username")
        if not v_id and not v_username and error_out_if_bad_data is True:
            return Response(
                {
                    ERROR: "Must give either `v_id` (int, volunteer ID number)"
                    " or `v_username` (str, the username of the person"
                    "you're looking for) in request json."
                }, status=status.HTTP_400_BAD_REQUEST
            )

        if v_id:
            return v_id
        if v_username:
            v = BlossomUser.objects.filter(username=v_username).first()
            if v:
                return v.id

        return None