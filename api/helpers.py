"""Helper classes which assist with retrieving volunteer info from requests."""
from blossom.authentication.models import BlossomUser
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from authentication.models import BlossomUser


class VolunteerMixin:
    """Mixin to retrieve volunteers based on information passed in a request."""

    @staticmethod
    def get_volunteer(
        volunteer_id: int = None, username: str = None
    ) -> [BlossomUser, None]:
        """
        Get the volunteer using the id or username supplied.

        If both are supplied, the id is used for the lookup.

        :param volunteer_id: the id of the specific volunteer
        :param username: the username of the specific volunteer
        :return: the volunteer, or None if the volunteer is not found
        """
        if volunteer_id:
            return BlossomUser.objects.filter(id=volunteer_id).first()
        if username:
            return BlossomUser.objects.filter(username=username).first()
        return None

    def get_volunteer_from_request(self, request: Request) -> [None, BlossomUser]:
        """
        Retrieve a volunteer from a request.

        The id and username are extracted from the request data for the lookup.

        :param request: the HTTP Request
        :return: the volunteer which is specified in the request data.
        """
        volunteer_id = request.data.get("v_id")
        username = request.data.get("username")

        return self.get_volunteer(volunteer_id=volunteer_id, username=username)


class RequestDataMixin:
    """Mixin to retrieve data from a request."""

    @staticmethod
    def get_volunteer_info_from_json(
        request: Request, error_out_if_bad_data: bool = False
    ) -> [None, int, Response]:
        """
        Retrieve the volunteer ID from the information provided in the request.

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
