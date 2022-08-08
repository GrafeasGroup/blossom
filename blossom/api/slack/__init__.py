"""Utilities for Slack related functionality."""
import os
from unittest import mock

from django.conf import settings
from slack import WebClient

from blossom.errors import ConfigurationError

if settings.ENABLE_SLACK is True:
    try:
        client = WebClient(token=os.environ["SLACK_API_KEY"])  # pragma: no cover
    except KeyError:
        raise ConfigurationError(
            "ENABLE_SLACK is set to True, but no API key was found. Set the"
            " SLACK_API_KEY environment variable or change ENABLE_SLACK to False."
        )
else:
    # this is to explicitly disable posting to Slack when doing local dev
    client = mock.Mock()
