from datetime import datetime, timedelta
from unittest.mock import patch

import pytz
from django.test import Client

from blossom.api.models import TranscriptionCheck
from blossom.api.slack.commands.info import user_info_text
from blossom.utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    setup_user_client,
)


def test_user_info_text_new_user(client: Client) -> None:
    """Verify that the string for a new user is generated correctly."""
    client, headers, user = setup_user_client(
        client,
        id=123,
        username="Userson",
        date_joined=datetime(2021, 5, 21, tzinfo=pytz.UTC),
        accepted_coc=False,
        is_bot=False,
    )

    expected = """Info about *<https://reddit.com/u/Userson|u/Userson>*:

*General*:
- Gamma: 0 Γ (0 Γ in last 2 weeks)
- Joined on: 2021-05-21 (1.0 day ago)
- Last active: Never

*Transcription Quality*:
- Checks: 0 (0.0% of transcriptions)
- Warnings: 0 (0.0% of checks)
- Comments: 0 (0.0% of checks)
- Watch status: Automatic (100.0%)

*Debug Info*:
- ID: `123`
- Blocked: No
- Bot: No
- Accepted CoC: No"""

    with patch(
        "blossom.api.slack.commands.info.timezone.now",
        return_value=datetime(2021, 5, 22, tzinfo=pytz.UTC),
    ):
        actual = user_info_text(user)

    assert actual == expected


def test_user_info_text_old_user(client: Client) -> None:
    """Verify that the string for a new user is generated correctly."""
    client, headers, user = setup_user_client(
        client,
        id=123,
        username="Userson",
        date_joined=datetime(2020, 4, 21, tzinfo=pytz.UTC),
        accepted_coc=True,
        is_bot=False,
    )

    tr_data = [
        (datetime(2020, 7, 3, tzinfo=pytz.UTC), True, True, False),
        (datetime(2020, 7, 7, tzinfo=pytz.UTC), False, False, False),
        (datetime(2020, 7, 9, tzinfo=pytz.UTC), False, False, False),
        (datetime(2021, 4, 10, tzinfo=pytz.UTC), True, False, True),
        (datetime(2021, 4, 12, tzinfo=pytz.UTC), True, False, False),
    ]

    for idx, (date, has_check, is_comment, is_warning) in enumerate(tr_data):
        submission = create_submission(
            id=100 + idx,
            create_time=date - timedelta(days=1),
            claim_time=date,
            complete_time=date + timedelta(days=1),
            claimed_by=user,
            completed_by=user,
        )
        transcription = create_transcription(
            submission, user, id=200 + idx, create_time=date
        )

        if has_check:
            check_status = TranscriptionCheck.TranscriptionCheckStatus
            status = (
                check_status.COMMENT_RESOLVED
                if is_comment
                else check_status.WARNING_RESOLVED
                if is_warning
                else check_status.APPROVED
            )
            create_check(transcription, status=status)

    expected = """Info about *<https://reddit.com/u/Userson|u/Userson>*:

*General*:
- Gamma: 5 Γ (2 Γ in last 2 weeks)
- Joined on: 2020-04-21 (1.0 year ago)
- Last active: 2021-04-13 (1.1 weeks ago)

*Transcription Quality*:
- Checks: 3 (60.0% of transcriptions)
- Warnings: 1 (33.3% of checks)
- Comments: 1 (33.3% of checks)
- Watch status: Automatic (100.0%)

*Debug Info*:
- ID: `123`
- Blocked: No
- Bot: No
- Accepted CoC: Yes"""

    with patch(
        "blossom.api.slack.commands.info.timezone.now",
        return_value=datetime(2021, 4, 21, tzinfo=pytz.UTC),
    ):
        actual = user_info_text(user)

    assert actual == expected
