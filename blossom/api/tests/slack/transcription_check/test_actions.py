from datetime import datetime
from typing import Optional
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from blossom.api.models import TranscriptionCheck
from blossom.api.slack.transcription_check.actions import (
    _update_db_model,
    process_check_action,
)
from blossom.utils.test_helpers import (
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
        ("comment-pending", CheckStatus.COMMENT_UNFIXED, CheckStatus.COMMENT_PENDING),
        ("comment-resolved", CheckStatus.COMMENT_PENDING, CheckStatus.COMMENT_RESOLVED),
        ("comment-unfixed", CheckStatus.COMMENT_PENDING, CheckStatus.COMMENT_UNFIXED),
        ("warning-pending", CheckStatus.PENDING, CheckStatus.WARNING_PENDING),
        ("warning-pending", CheckStatus.WARNING_RESOLVED, CheckStatus.WARNING_PENDING),
        ("warning-pending", CheckStatus.WARNING_UNFIXED, CheckStatus.WARNING_PENDING),
        ("warning-resolved", CheckStatus.WARNING_PENDING, CheckStatus.WARNING_RESOLVED),
        ("warning-unfixed", CheckStatus.WARNING_PENDING, CheckStatus.WARNING_UNFIXED),
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
    client: Client,
    action: str,
    pre_status: CheckStatus,
    post_status: CheckStatus,
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
    "action",
    [
        "approved",
        "comment-resolved",
        "warning-resolved",
        "comment-unfixed",
        "warning-unfixed",
    ],
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
    "action",
    ["pending", "comment-pending", "warning-pending"],
)
def test_update_db_model_unset_complete_time(client: Client, action: str) -> None:
    """Test that the complete time is updated after reverting completion."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(
        transcription,
        moderator=mod,
        complete_time=timezone.now(),
    )
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
        "blossom.api.slack.transcription_check.actions.update_check_message",
        return_value=None,
    ) as mock, patch(
        "blossom.api.slack.transcription_check.actions.get_reddit_username",
        lambda _, us: us["name"],
    ):
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.APPROVED
        assert _is_time_recent(start, check.complete_time)
        assert mock.call_count == 1


def test_process_check_action_claim_own_transcription(client: Client) -> None:
    """Test that a mod cannot claim their own transcription."""
    setup_user_client(client, id=100)
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=mod, completed_by=mod)
    transcription = create_transcription(submission=submission, user=mod)
    check = create_check(transcription, id=123)
    assert check.moderator is None
    assert check.status == CheckStatus.PENDING

    # See https://api.slack.com/legacy/message-buttons
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [{"name": "Claim", "value": "check_claim_123", "type": "button"}],
        "user": {"id": "U045VRZFT", "name": "Moddington"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.transcription_check.actions.update_check_message",
        return_value=None,
    ) as update_mock, patch(
        "blossom.api.slack.transcription_check.actions.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock, patch(
        "blossom.api.slack.transcription_check.actions.get_reddit_username",
        lambda _, us: us["name"],
    ):
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.PENDING
        assert check.moderator is None
        assert update_mock.call_count == 1
        assert reply_mock.call_count == 1


def test_process_check_action_unknown_check(client: Client) -> None:
    """Test that an action with invalid check ID sends an error message."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(
        transcription,
        id=123,
        moderator=mod,
        slack_channel_id="C065W1189",
        slack_message_ts="1458170866.000004",
    )
    assert check.status == CheckStatus.PENDING

    # See https://api.slack.com/legacy/message-buttons
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [
            {"name": "Approve", "value": "check_approved_777", "type": "button"}
        ],
        "user": {"id": "U045VRZFT", "name": "Moddington"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.transcription_check.actions.update_check_message",
        return_value=None,
    ) as update_mock, patch(
        "blossom.api.slack.transcription_check.actions.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock, patch(
        "blossom.api.slack.transcription_check.actions.get_reddit_username",
        lambda _, us: us["name"],
    ):
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.PENDING
        assert check.complete_time is None
        assert update_mock.call_count == 0
        assert reply_mock.call_count == 1


def test_process_check_action_unknown_mod(client: Client) -> None:
    """Test that an action with an unknown Slack mod."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(
        transcription,
        id=123,
        slack_channel_id="C065W1189",
        slack_message_ts="1458170866.000004",
    )
    assert check.status == CheckStatus.PENDING

    # See https://api.slack.com/legacy/message-buttons
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [
            {"name": "Approve", "value": f"check_claim_{check.id}", "type": "button"}
        ],
        "user": {"id": "U045VRZFT", "name": "Impostor"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.transcription_check.actions.update_check_message",
        return_value=None,
    ) as update_mock, patch(
        "blossom.api.slack.transcription_check.actions.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock, patch(
        "blossom.api.slack.transcription_check.actions.get_reddit_username",
        lambda _, us: us["name"],
    ):
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.PENDING
        assert check.moderator is None
        assert update_mock.call_count == 0
        assert reply_mock.call_count == 1


def test_process_check_action_no_mod(client: Client) -> None:
    """Test that an action for an unclaimed check fails."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    create_user(id=200, username="Moddington")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(
        transcription,
        id=123,
        moderator=None,
        slack_channel_id="C065W1189",
        slack_message_ts="1458170866.000004",
    )
    assert check.moderator is None

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

    with patch(
        "blossom.api.slack.transcription_check.actions.update_check_message",
        return_value=None,
    ) as update_mock, patch(
        "blossom.api.slack.transcription_check.actions.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock, patch(
        "blossom.api.slack.transcription_check.actions.get_reddit_username",
        lambda _, us: us["name"],
    ):
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.PENDING
        assert check.moderator is None
        assert update_mock.call_count == 1
        assert reply_mock.call_count == 1


def test_process_check_action_wrong_mod(client: Client) -> None:
    """Test that an action fails if the mod is not the one who claimed the check."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    create_user(id=300, username="Impostor")
    submission = create_submission(claimed_by=user, completed_by=user)
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(
        transcription,
        id=123,
        moderator=mod,
        slack_channel_id="C065W1189",
        slack_message_ts="1458170866.000004",
    )

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
        "user": {"id": "U045VRZFT", "name": "Impostor"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.transcription_check.actions.update_check_message",
        return_value=None,
    ) as update_mock, patch(
        "blossom.api.slack.transcription_check.actions.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock, patch(
        "blossom.api.slack.transcription_check.actions.get_reddit_username",
        lambda _, us: us["name"],
    ):
        process_check_action(data)

        check.refresh_from_db()

        assert check.status == CheckStatus.PENDING
        assert check.moderator == mod
        assert update_mock.call_count == 1
        assert reply_mock.call_count == 1
