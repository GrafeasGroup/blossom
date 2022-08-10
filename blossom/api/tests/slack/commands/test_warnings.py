# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from datetime import datetime
from unittest.mock import patch

from django.test import Client

from blossom.api.models import TranscriptionCheck
from blossom.api.slack.commands.warnings import (
    _get_warning_checks,
    _warning_entry,
    _warning_text,
    warnings_cmd,
)
from blossom.strings import translation
from blossom.utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    setup_user_client,
)

i18n = translation()

CheckStatus = TranscriptionCheck.TranscriptionCheckStatus


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
        status=CheckStatus.WARNING_RESOLVED,
    )

    expected = i18n["slack"]["warnings"]["warning_entry"].format(
        date="2022-02-03",
        source="r/CuratedTumblr",
        check_url="https://example.com/check",
        tr_url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )

    with patch(
        "blossom.api.models.TranscriptionCheck.get_slack_url",
        return_value="https://example.com/check",
    ):
        actual = _warning_entry(check)

    assert actual == expected


def test_get_warning_checks(client: Client) -> None:
    """Test that a warning checks are filtered correctly."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")

    check_properties = [
        (10, CheckStatus.COMMENT_PENDING),
        (11, CheckStatus.COMMENT_RESOLVED),
        (12, CheckStatus.PENDING),
        (13, CheckStatus.WARNING_PENDING),
        (14, CheckStatus.WARNING_RESOLVED),
        (15, CheckStatus.WARNING_UNFIXED),
        (16, CheckStatus.APPROVED),
    ]

    for (ch_id, status) in check_properties:
        submission = create_submission(
            claimed_by=user,
            completed_by=user,
        )
        transcription = create_transcription(
            submission=submission, user=user, create_time=datetime(2022, 3, 2, ch_id)
        )
        create_check(transcription=transcription, status=status, id=ch_id)

    actual = _get_warning_checks(user)

    assert [check.id for check in actual] == [13, 14, 15]


def test_warning_text_no_warnings(client: Client) -> None:
    """Test that other text is displayed if no warnings are available."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")

    check_properties = [
        (10, CheckStatus.COMMENT_PENDING),
        (11, CheckStatus.COMMENT_RESOLVED),
        (12, CheckStatus.PENDING),
        (15, CheckStatus.APPROVED),
    ]

    for (ch_id, status) in check_properties:
        submission = create_submission(
            claimed_by=user,
            completed_by=user,
        )
        transcription = create_transcription(
            submission=submission, user=user, create_time=datetime(2022, 3, 2, ch_id)
        )
        create_check(transcription=transcription, status=status, id=ch_id)

    expected = i18n["slack"]["warnings"]["no_warnings"].format(username="Userson")
    actual = _warning_text(user)

    assert actual == expected


def test_warnings_cmd(client: Client) -> None:
    client, headers, user = setup_user_client(client, id=100, username="Userson")

    with patch(
        "blossom.api.slack.commands.warnings._warning_text", return_value="Text"
    ) as txt_mock, patch(
        "blossom.api.slack.commands.warnings.client.chat_postMessage"
    ) as msg_mock:
        warnings_cmd(channel="", message="warnings Userson")

        assert txt_mock.call_count == 1
        assert txt_mock.call_args[0][0] == user

        assert msg_mock.call_count == 1
        assert msg_mock.call_args[1]["text"] == "Text"
