from django_hosts import patterns, host
from django.conf import settings

host_patterns = patterns(
    '',
    host(r'api', 'blossom.api.urls', name='api'),
    host(r'payments', 'blossom.payments.urls', name='payments'),
    host(r'engineering', 'blossom.engineeringblog.urls', name='engineeringblog'),
    host(r'wiki', 'blossom.wiki.urls', name='wiki'),
    host(r'', settings.ROOT_URLCONF, name='www'),  # must always be last
)
