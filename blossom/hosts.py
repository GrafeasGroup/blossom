from django_hosts import patterns, host
from django.conf import settings

host_patterns = patterns(
    '',
    host(r'api', 'blossom.api.urls', name='api'),
    host(r'payments', 'blossom.payments.urls', name='payments'),
    host(r'', settings.ROOT_URLCONF, name='www')
)
