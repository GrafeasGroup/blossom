from typing import Union

from social_core.backends.base import BaseAuth

from blossom.authentication.models import BlossomUser


def load_user(
    backend: BaseAuth, *args: list, details: dict = None, **kwargs: dict
) -> Union[None, dict]:
    """Match the returned user from Reddit to the username that we already have."""
    if backend.name == "reddit":
        user = BlossomUser.objects.filter(
            username__iexact=details.get("username")
        ).first()
        if user:
            return {"user": user}
