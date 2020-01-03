from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from blossom.authentication.models import BlossomUser

ERROR = "error"
SUCCESS = "success"


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
                    " you're looking for) in request json."
                }, status=status.HTTP_400_BAD_REQUEST
            )

        if v_id:
            return v_id
        if v_username:
            if v := BlossomUser.objects.filter(username=v_username).first():
                return v.id

        return None
