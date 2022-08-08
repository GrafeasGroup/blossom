import pytest
from django.core.exceptions import ImproperlyConfigured
from pytest_django.fixtures import SettingsWrapper

from blossom.website.helpers import get_additional_context
from blossom.website.models import Post


def test_setup_site_check() -> None:
    """
    Verify that the bootstrap command must be run.

    Because the bootstrap command auto-runs on every test, we have to manually
    fake that it _hasn't_ run.
    """
    Post.objects.all().delete()
    with pytest.raises(ImproperlyConfigured):
        get_additional_context({})


def test_bootstrap_check(settings: SettingsWrapper) -> None:
    """
    Verify that the bootstrap command must be run.

    Because the bootstrap command auto-runs on every test, we have to manually
    fake that it _hasn't_ run.
    """
    Post.objects.all().delete()
    settings.ENVIRONMENT = "prod"

    with pytest.raises(ImproperlyConfigured):
        get_additional_context({})
