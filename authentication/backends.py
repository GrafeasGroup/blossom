"""Authentication backend for the application."""
from typing import Union

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


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
