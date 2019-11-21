from django_hosts import patterns, host
from django.conf import settings

host_patterns = patterns(
    '',
    host(r'www', settings.ROOT_URLCONF, name='www'),
    host(r'api', 'blossom.api.urls', name='api'),
    host(r'payments', 'blossom.payments.urls', name='payments')
)
