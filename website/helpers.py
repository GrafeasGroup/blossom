from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

from website.models import Post


def get_additional_context(context):
    context["navbar"] = Post.objects.filter(
        Q(published=True) & Q(standalone_section=True)
    ).order_by("header_order")
    try:
        context["tos"] = Post.objects.get(slug="terms-of-service")
    except Post.DoesNotExist:
        if settings.ENVIRONMENT == "testing":
            raise ImproperlyConfigured(
                "The test site is not built yet; did you remember to add the"
                " `setup_site` fixture?"
            )
        else:
            raise ImproperlyConfigured(
                "Bootstrap command has not yet been run; `python manage.py"
                " bootstrap` on prod or `python manage.py bootstrap"
                " --settings=blossom.local_settings` on dev."
            )
    return context


def grafeas_staff_required(
    view_func=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    """
    Decorator for views that checks that the user is logged in and is a staff
    member, redirecting to the login page if necessary.
    """
    if not login_url:
        login_url = settings.LOGIN_URL
    actual_decorator = user_passes_test(
        # superadmins should be allowed in too
        lambda u: u.is_active and (u.is_grafeas_staff or u.is_staff),
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator
