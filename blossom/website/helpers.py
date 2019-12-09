from django.db.models import Q
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from blossom.website.models import Post

def get_additional_context(context):
    context['navbar'] = Post.objects.filter(Q(published=True) & Q(standalone_section=True)).order_by('header_order')
    try:
        context['tos'] = Post.objects.get(slug='terms-of-service')
    except Post.DoesNotExist:
        if settings.ENVIRONMENT == 'testing':
            raise ImproperlyConfigured(
                "The test site is not built yet; did you remember to add the"
                " `setup_site` fixture?"
            )
        else:
            raise ImproperlyConfigured(
                "Cannot find the terms of service post; did you run the bootstrap"
                " command? `python manage.py bootstrap` on prod or `python manage.py"
                " bootstrap --settings=blossom.local_settings` on dev."
            )
    return context
