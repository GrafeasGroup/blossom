"""Authentication backend for the application."""
from typing import Tuple, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework.request import Request

from blossom.authentication.models import BlossomUser


class EmailBackend(ModelBackend):
    """
    Custom backend which uses the email instead of the username to login.

    Note that this backend is copied from https://stackoverflow.com/a/37332393.
    """

    def authenticate(
        self, username: str = None, password: str = None, **kwargs: object
    ) -> Union[User, None]:
        """
        Authenticate the user if proper authentication is provided.

        Note that the username parameter is abused to instead be the email address
        of the user, which is in turn used to authenticate. This is in line with
        https://stackoverflow.com/a/37332393.

        :param username: the email address to authenticate with
        :param password: the password belonging to said email address
        :param kwargs: possible keyword arguments, although ignored in this method
        :return: either the corresponding user when authenticated or None otherwise
        """
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=username)
        except user_model.DoesNotExist:
            return None
        else:
            return user if user.check_password(password) else None


class BlossomRestFrameworkAuth(authentication.BaseAuthentication):
    def authenticate(self, request: Request) -> Tuple[BlossomUser, bool]:
        """
        Handle authentication for the API side.

        DRF needs to handle authentication in a tuple as opposed to a boolean,
        so it's easier to just expand it into its own type of auth handler.

        The first check is for standard API interactions involving the BlossomAPI
        class. Username + password. The second check (SessionAuthentication) is
        used for the web interface -- log in through the front end and browse the
        API as an authenticated user.
        """
        if user := EmailBackend().authenticate(
            username=request.data.get("email"), password=request.data.get("password")
        ):
            return (user, None)

        if user_data := authentication.SessionAuthentication().authenticate(request):
            if user_data[0].is_staff or user_data[0].is_grafeas_staff:
                return user_data

        return None
