from datetime import datetime
from typing import Optional

import pytest
from django.test import Client
from django.utils import timezone

from api.models import TranscriptionCheck
from api.slack.transcription_check.actions import _update_db_model
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
