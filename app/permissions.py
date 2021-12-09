from functools import wraps
from typing import Any, Callable

from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, reverse

from app.middleware import refresh_token


def require_coc(func: Callable) -> Any:
    """Enforce code of conduct acceptance."""

    @wraps(func)
    def inner_func(request: HttpRequest, *args: list, **kwargs: dict) -> Any:
        if not request.user.accepted_coc:
            return redirect("accept_coc")
        return func(request, *args, **kwargs)

    return inner_func


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
        if not request.user.social_auth.first():
            # Don't do anything if we don't have social auth hooked up
            return login_error(request)
        if not hasattr(request.user.social_auth.first(), "extra_data"):
            # Safety check; make sure the extra data dict exists
            return login_error(request)
        if not request.user.social_auth.first().extra_data.get("refresh_token"):
            # We won't have a refresh token if we just started the process
            refresh_token(request)

        return func(request, *args, **kwargs)

    return inner_func
