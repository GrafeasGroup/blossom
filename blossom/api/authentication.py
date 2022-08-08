from __future__ import annotations

from typing import TYPE_CHECKING

import rest_framework.permissions as rfperms
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.request import Request

if TYPE_CHECKING:  # pragma: no cover
    # Python doesn't have great handling of circular imports for type checking
    # purposes. Because View is only required for type checking, we can lock
    # it behind the above statement. TYPE_CHECKING will always evaluate to False
    # at runtime and will evaluate to True when run with an external checker.
    # For more information on this, see the following:
    # - https://stackoverflow.com/a/39757388
    # - https://www.python.org/dev/peps/pep-0563/

    # noinspection PyUnresolvedReferences
    from rest_framework.views import View


class AdminApiKeyCustomCheck(rfperms.BasePermission):
    """Permission check which determines whether the user is a valid admin."""

    message = "Sorry, this resource can only be accessed by an admin API key."

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Check whether the user is a valid admin.

        :param request: the request which is evaluated
        :param view: the view to which the request is sent
        :return: whether the user is a valid admin or not
        """
        if settings.OVERRIDE_API_AUTH:
            return True

        if not isinstance(request.user, AnonymousUser):
            if request.user.api_key:
                # Retrieve the contents of the "Authorization" key from either
                # the META or the headers of the request.
                request_key = request.META.get(
                    "Authorization", request.headers.get("Authorization", "").split()
                )
                if len(request_key) >= 2:
                    return all(
                        [
                            request_key[0] == "Api-Key",
                            request.user.api_key.is_valid(request_key[1]),
                            request.user.is_grafeas_staff or request.user.is_staff,
                        ]
                    )
        return False


class BlossomApiPermission(rfperms.BasePermission):
    """Combined check of either the AdminApiKeyCustomCheck or the default Admin Check."""

    # For some reason, combining the different auth patterns in the settings
    # file fails miserably and will default to HasAPIKey if it's enabled.
    # I've spent far too long screwing with this, so here's a permission
    # class that manually checks both of them and returns true if either one
    # of them is valid.

    message = "Sorry, this resource can only be accessed by an admin."

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Check whether the user is an admin through either of the two definitions.

        These definitions are determined either through our custom admin check,
        or the default check supplied by Django REST.

        :param request: the request which is evaluated
        :param view: the view to which the request is sent
        :return: whether the user is a valid admin or not
        """
        return any(
            [
                rfperms.IsAdminUser().has_permission(request, view),
                AdminApiKeyCustomCheck().has_permission(request, view),
            ]
        )
