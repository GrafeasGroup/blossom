from typing import Dict

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils import timezone

from blossom.authentication.models import BlossomUser

ERROR = "error"
SUCCESS = "success"

def build_response(
    result: str, message: str, status_code: int, data: Dict = None
) -> Response:
    resp = {"result": result, "message": message, "server_time": timezone.now()}
    if data:
        resp.update({"data": data})
    return Response(resp, status=status_code)


class VolunteerMixin(object):
    def get_volunteer(
        self, id: int = None, username: str = None
    ) -> [BlossomUser, None]:
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
    def get_volunteer_info_from_json(
            self,
            request: Request,
            error_out_if_bad_data=False
    ) -> [None, int, Response]:
        """
        Retrieve the volunteer ID from the information provided in the HTTP
        body of the provided request.

        Note that this method returns either the ID of the corresponding
        volunteer or an error Response when this is not possible.

        Returned error responses are the following:
        - 400: There is none of the following fields in the HTTP body:
            - v_id
            - v_username
            - username

        :param request: the request to extract the information from
        :param error_out_if_bad_data: whether to throw an error response or None
        :return: either an int if the volunteer is found, or None or Response
                 depending on the provided boolean

        """
        v_id = request.data.get("v_id")
        v_username = request.data.get("v_username") or request.data.get("username")
        if not v_id and not v_username and error_out_if_bad_data is True:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if v_id:
            return v_id
        if v_username:
            if v := BlossomUser.objects.filter(username=v_username).first():
                return v.id

        return None


# def send_to_modchat(username: str=None, icon_url: str=None, text: str=None, channel: str=None)
