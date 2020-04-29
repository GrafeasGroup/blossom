from typing import Dict

from rest_framework import status
from rest_framework.response import Response

from authentication.models import BlossomUser


class BlossomUserMixin:
    REQUEST_FIELDS = {"v_id": "id", "v_username": "username", "username": "username"}

    def get_user_from_request(self, data: Dict) -> [BlossomUser, Response]:
        """
        Retrieve the BlossomUser based on information provided within the request data.

        The user can be retrieved by its ID and / or its username using a combination of
        any of the following keys:
            - username:   The username
            - v_id:       The user ID
            - v_username: The username

        Note that when multiple values are present within the request, the user with
        the combination of these values is found.

        When either none of the above keys is provided or no user with the provided
        combination is found, a Response with a 400 and 404 status is returned
        respectively.

        :param data: the dictionary from which data is used to retrieve the user
        :return: the requested user or an error Response based on errors
        """
        if not any(key in data for key in self.REQUEST_FIELDS.keys()):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Filter the BlossomUsers on fields present in the request data according to the
        # mapping in the REQUEST_FIELDS constant.
        user = BlossomUser.objects.filter(
            **{
                self.REQUEST_FIELDS[key]: value
                for key, value in data.items()
                if key in self.REQUEST_FIELDS.keys()
            }
        ).first()
        return user if user else Response(status=status.HTTP_404_NOT_FOUND)
