import pytest
from django.core.exceptions import ImproperlyConfigured

from blossom.website.helpers import get_additional_context


def test_setup_site_check():
    with pytest.raises(ImproperlyConfigured):
        get_additional_context({})


def test_bootstrap_check(settings):
    settings.ENVIRONMENT = 'prod'

    with pytest.raises(ImproperlyConfigured):
        get_additional_context({})
