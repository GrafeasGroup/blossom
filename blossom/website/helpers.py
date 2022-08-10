from typing import Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

from blossom.website.models import Post


def get_additional_context(context: Dict = None) -> Dict:
    """Build the default context dictionary for the views."""
    if not context:
        context = {}
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
