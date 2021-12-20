from typing import Callable

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test


def grafeas_staff_required(
    view_func: Callable = None,
    redirect_field_name: str = REDIRECT_FIELD_NAME,
    login_url: str = None,
) -> Callable:
    """
    Login decorator for functions.

    Decorator for view functions that checks that the user is logged in and is a staff
    member, redirecting to the login page if necessary.
    """
    if not login_url:
        login_url = settings.LOGIN_URL
    actual_decorator = user_passes_test(
        # superadmins should be allowed in too
        lambda u: u.is_authenticated and (u.is_grafeas_staff or u.is_staff),
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator
