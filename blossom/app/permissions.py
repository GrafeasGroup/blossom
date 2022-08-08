from functools import wraps
from typing import Any, Callable

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, reverse
from django.utils.decorators import method_decorator

from blossom.app.middleware import refresh_token


def require_coc(func: Callable) -> Any:
    """Enforce code of conduct acceptance."""

    @wraps(func)
    def inner_func(request: HttpRequest, *args: list, **kwargs: dict) -> Any:
        if not request.user.accepted_coc:
            return redirect("accept_coc")
        return func(request, *args, **kwargs)

    return inner_func


class RequireCoCMixin:
    # https://stackoverflow.com/a/53065028
    @method_decorator(require_coc)
    def dispatch(self, *args: object, **kwargs: object) -> object:
        """Apply the decorator to the class."""
        return super().dispatch(*args, **kwargs)


def require_reddit_auth(func: Callable) -> Any:
    """Enforce logging in with your Reddit account."""

    def login_error(request: HttpRequest) -> HttpResponseRedirect:
        """Handle generic authentication issues with Reddit."""
        logout(request)
        messages.error(
            request,
            "Something is wrong with our connection with Reddit."
            " Please re-authenticate your account.",
        )
        path = reverse("login") + "?next=/app/"
        return redirect(path)

    @wraps(func)
    def inner_func(request: HttpRequest, *args: list, **kwargs: dict) -> Any:
        if not settings.ENABLE_REDDIT:
            return func(request, *args, **kwargs)
        social_auth = request.user.social_auth.filter(provider="reddit").first()
        if not social_auth:
            # Don't do anything if we don't have social auth hooked up
            return login_error(request)
        if not hasattr(social_auth, "extra_data"):
            # Safety check; make sure the extra data dict exists
            return login_error(request)
        if not social_auth.extra_data.get("refresh_token"):
            # We won't have a refresh token if we just started the process
            refresh_token(request)

        return func(request, *args, **kwargs)

    return inner_func
