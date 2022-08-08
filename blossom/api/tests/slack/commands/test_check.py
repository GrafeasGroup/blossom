# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from unittest.mock import patch

import pytest
from django.test import Client

from blossom.api.models import TranscriptionCheck
from blossom.api.slack.commands import check_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    setup_user_client,
)

i18n = translation()


@pytest.mark.parametrize(
    "url",
    [
        # Normal URLs
        "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
        "https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
        # Slack link
        "<https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/>",
        "<https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/>",
        "<https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/>",
        # Named Slack link
        "<https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/|Tor_Post>",
        "<https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/|Partner_Post>",
        "<https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/|Transcription>",
        # Wrong casing
        "https://reddit.com/r/transcribersofreddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/curatedtumblr/comments/t315gq/linguistics_fax/",
        "https://www.reddit.com/r/curatedtumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    ],
)
def test_check_cmd(client: Client, url: str) -> None:
    """Test that the check command generates a new check."""
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
    )

    with patch(
        "blossom.api.slack.commands.check.client.chat_postMessage"
    ) as message_mock, patch(
        "blossom.api.slack.commands.check.send_check_message"
    ) as check_mock, patch(
        "blossom.api.slack.commands.check.client.chat_getPermalink"
    ) as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 1
        assert link_mock.call_count == 1

        checks = TranscriptionCheck.objects.filter(transcription=transcription)
        assert len(checks) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
        "https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    ],
)
def test_check_cmd_existing_check(client: Client, url: str) -> None:
    """Test check command if a check already exists for the transcription."""
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
        url="https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )
    create_check(
        transcription=transcription, slack_channel_id="asd", slack_message_ts="1234"
    )

    checks = TranscriptionCheck.objects.filter(transcription=transcription)
    assert len(checks) == 1

    with patch(
        "blossom.api.slack.commands.check.client.chat_postMessage"
    ) as message_mock, patch(
        "blossom.api.slack.commands.check.send_check_message"
    ) as check_mock, patch(
        "blossom.api.slack.commands.client.chat_getPermalink"
    ) as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 0
        assert link_mock.call_count == 1

        checks = TranscriptionCheck.objects.filter(transcription=transcription)
        assert len(checks) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    ],
)
def test_check_cmd_no_transcription(client: Client, url: str) -> None:
    """Test check command if the submission does not have a transcription."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    create_submission(
        claimed_by=user,
        completed_by=user,
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    )

    with patch(
        "blossom.api.slack.commands.check.client.chat_postMessage"
    ) as message_mock, patch(
        "blossom.api.slack.commands.check.send_check_message"
    ) as check_mock, patch(
        "blossom.api.slack.commands.check.client.chat_getPermalink"
    ) as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 0
        assert link_mock.call_count == 0


@pytest.mark.parametrize(
    "url",
    [
        "asdf",
        "https://reddit.com/r/TranscribersOfReddit/comments/t31zvj/curatedtumblr_image_love_and_languages/",
        "https://reddit.com/r/CuratedTumblr/comments/t31xsx/love_and_languages/",
        "https://reddit.com/r/CuratedTumblr/comments/t31xsx/love_and_languages/hypsf0v/",
    ],
)
def test_check_cmd_unknown_url(client: Client, url: str) -> None:
    """Test check command if a check already exists for the transcription."""
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
        url="https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )
    create_check(
        transcription=transcription, slack_channel_id="asd", slack_message_ts="1234"
    )

    with patch(
        "blossom.api.slack.commands.check.client.chat_postMessage"
    ) as message_mock, patch(
        "blossom.api.slack.commands.check.send_check_message"
    ) as check_mock, patch(
        "blossom.api.slack.commands.check.client.chat_getPermalink"
    ) as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 0
        assert link_mock.call_count == 0
