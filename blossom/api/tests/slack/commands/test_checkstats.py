from datetime import datetime
from unittest.mock import patch

import pytz
from django.test import Client

from blossom.api.models import TranscriptionCheck
from blossom.api.slack.commands.checkstats import check_stats_msg
from blossom.utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)


def test_check_stats_msg(client: Client) -> None:
    """Verify that the string for a new user is generated correctly."""
    client, headers, user = setup_user_client(
        client,
        id=123,
        username="Userson",
    )
    mod = create_user(id=456, username="Moddington")
    other_mod = create_user(id=789, username="Other")

    check_status = TranscriptionCheck.TranscriptionCheckStatus

    check_data = [
        (datetime(2020, 7, 3), check_status.APPROVED, mod),
        (datetime(2020, 7, 4), check_status.COMMENT_PENDING, mod),
        (datetime(2020, 7, 5), check_status.WARNING_RESOLVED, mod),
        (datetime(2020, 7, 6), check_status.APPROVED, other_mod),
        (
            datetime(2020, 7, 7),
            check_status.COMMENT_PENDING,
            other_mod,
        ),
        (datetime(2020, 7, 8), check_status.APPROVED, other_mod),
        # Recent
        (datetime(2020, 7, 9), check_status.APPROVED, mod),
        (datetime(2020, 7, 10), check_status.APPROVED, mod),
        (datetime(2020, 7, 11), check_status.COMMENT_RESOLVED, mod),
        (datetime(2020, 7, 12), check_status.COMMENT_RESOLVED, mod),
        (datetime(2020, 7, 13), check_status.APPROVED, other_mod),
        (datetime(2020, 7, 14), check_status.WARNING_RESOLVED, other_mod),
    ]

    for idx, (date, status, mod_usr) in enumerate(check_data):
        submission = create_submission(id=100 + idx)
        date: datetime = date.astimezone(pytz.UTC)
        transcription = create_transcription(
            submission,
            user,
            id=200 + idx,
            create_time=date,
        )
        create_check(
            transcription,
            moderator=mod_usr,
            create_time=date,
            complete_time=date,
            status=status,
        )

    expected = """Mod check stats for *<https://reddit.com/u/Moddington|u/Moddington>*:

*Completed Checks*:
- All-time: 7 (58.3% of all checks)
- Last 2 weeks: 4 (66.7% of all recent checks)
- Last completed: 2020-07-12 (1.6 weeks ago)

*Completed Warnings*:
- All-time: 1 (14.3% of checks, 50.0% of all warnings)
- Last 2 weeks: 0 (0.0% of recent checks, 0.0% of all recent warnings)
- Last completed: 2020-07-05 (2.6 weeks ago)

*Completed Comments*:
- All-time: 3 (42.9% of checks, 75.0% of all comments)
- Last 2 weeks: 2 (50.0% of recent checks, 100.0% of all recent comments)
- Last completed: 2020-07-12 (1.6 weeks ago)"""

    with patch(
        "blossom.api.slack.commands.checkstats.timezone.now",
        return_value=datetime(2020, 7, 23, tzinfo=pytz.UTC),
    ):
        actual = check_stats_msg(mod)

    assert actual == expected
