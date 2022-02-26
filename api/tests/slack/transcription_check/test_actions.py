from datetime import datetime
from typing import Optional
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from api.models import TranscriptionCheck
from api.slack.transcription_check.actions import _update_db_model, process_check_action
from utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)

CheckStatus = TranscriptionCheck.TranscriptionCheckStatus


def _is_time_recent(start: datetime, time: Optional[datetime]) -> bool:
    """Determine whether the given time indicates the current time.

    :param start: The start time before the given time was created.
    :param time: The time to check.
    """
    if time is None:
        return False

    return start <= time <= timezone.now()


@pytest.mark.parametrize(
    "action,pre_status,post_status",
    [
        ("approved", CheckStatus.PENDING, CheckStatus.APPROVED),
        ("comment-pending", CheckStatus.PENDING, CheckStatus.COMMENT_PENDING),
        ("comment-pending", CheckStatus.COMMENT_RESOLVED, CheckStatus.COMMENT_PENDING),
        ("comment-resolved", CheckStatus.COMMENT_PENDING, CheckStatus.COMMENT_RESOLVED),
        ("warning-pending", CheckStatus.PENDING, CheckStatus.WARNING_PENDING),
        ("warning-pending", CheckStatus.WARNING_RESOLVED, CheckStatus.WARNING_PENDING),
        ("warning-resolved", CheckStatus.WARNING_PENDING, CheckStatus.WARNING_RESOLVED),
        ("pending", CheckStatus.COMMENT_PENDING, CheckStatus.PENDING),
        ("pending", CheckStatus.WARNING_PENDING, CheckStatus.PENDING),
        ("claim", CheckStatus.PENDING, CheckStatus.PENDING),
        ("claim", CheckStatus.COMMENT_PENDING, CheckStatus.COMMENT_PENDING),
        ("claim", CheckStatus.WARNING_PENDING, CheckStatus.WARNING_PENDING),
        ("unclaim", CheckStatus.PENDING, CheckStatus.PENDING),
        ("unclaim", CheckStatus.COMMENT_PENDING, CheckStatus.COMMENT_PENDING),
        ("unclaim", CheckStatus.WARNING_PENDING, CheckStatus.WARNING_PENDING),
    ],
)
def test_update_db_model_status(
    client: Client, action: str, pre_status: CheckStatus, post_status: CheckStatus,
) -> None:
    """Test the updating of the status of the check DB model."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription, moderator=mod, status=pre_status)

    assert check.status == pre_status

    assert _update_db_model(check, mod, action)
    check.refresh_from_db()

    assert check.status == post_status


def test_update_db_model_claim(client: Client) -> None:
    """Test the updating of the check DB model after claiming."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription)
    assert check.moderator is None
    assert check.claim_time is None

    start = timezone.now()
    assert _update_db_model(check, mod, "claim")
    check.refresh_from_db()

    assert check.moderator == mod
    assert _is_time_recent(start, check.claim_time)


def test_update_db_model_unclaim(client: Client) -> None:
    """Test the updating of the check DB model after unclaiming."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription, moderator=mod, claim_time=timezone.now())
    assert check.moderator == mod
    assert check.claim_time is not None

    assert _update_db_model(check, mod, "unclaim")
    check.refresh_from_db()

    assert check.moderator is None
    assert check.claim_time is None


@pytest.mark.parametrize(
    "action", ["approved", "comment-resolved", "warning-resolved"],
)
def test_update_db_model_set_complete_time(client: Client, action: str) -> None:
    """Test that the complete time is updated after completing a check."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription, moderator=mod)
    assert check.complete_time is None

    start = timezone.now()
    assert _update_db_model(check, mod, action)
    check.refresh_from_db()

    assert _is_time_recent(start, check.complete_time)


@pytest.mark.parametrize(
    "action", ["pending", "comment-pending", "warning-pending"],
)
def test_update_db_model_unset_complete_time(client: Client, action: str) -> None:
    """Test that the complete time is updated after reverting completion."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription, moderator=mod, complete_time=timezone.now(),)
    assert check.complete_time is not None

    assert _update_db_model(check, mod, action)
    check.refresh_from_db()

    assert check.complete_time is None


def test_update_db_model_unknown_action(client: Client) -> None:
    """Test that the update returns False if the action is unknown."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription, moderator=mod)

    assert not _update_db_model(check, mod, "pasdpajsdp")


def test_process_check_action(client: Client) -> None:
    """Test that an expected check action runs correctly."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(
        transcription,
        moderator=mod,
        slack_channel_id="C065W1189",
        slack_message_ts="1458170866.000004",
    )
    assert check.status == CheckStatus.PENDING

    # See https://api.slack.com/legacy/message-buttons
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [
            {
                "name": "Approve",
                "value": f"check_approved_{check.id}",
                "type": "button",
            }
        ],
        "user": {"id": "U045VRZFT", "name": "Moddington"},
        "message_ts": "1458170866.000004",
    }

    start = timezone.now()

    with patch(
        "api.slack.transcription_check.actions.update_check_message", return_value=None
    ) as mock:
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.APPROVED
        assert _is_time_recent(start, check.complete_time)
        assert mock.call_count == 1
