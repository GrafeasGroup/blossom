# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from datetime import datetime
from unittest.mock import patch

from django.test import Client

from api.models import TranscriptionCheck
from api.slack.commands.warnings import _warning_entry
from blossom.strings import translation
from utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    setup_user_client,
)

i18n = translation()


def test_warning_entry(client: Client) -> None:
    """Test that a warning entry is generated correctly."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")

    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    )
    transcription = create_transcription(
        submission=submission,
        user=user,
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
        create_time=datetime(2022, 2, 3, 13, 2),
    )
    check = create_check(
        transcription=transcription,
        status=TranscriptionCheck.TranscriptionCheckStatus.WARNING_RESOLVED,
    )

    expected = i18n["slack"]["warnings"]["warning_entry"].format(
        date="2022-02-03",
        source="r/CuratedTumblr",
        check_url="https://example.com/check",
        tr_url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )

    with patch(
        "api.models.TranscriptionCheck.get_slack_url",
        return_value="https://example.com/check",
    ):
        actual = _warning_entry(check)

    assert actual == expected
