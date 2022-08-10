from unittest.mock import patch

from django.test import Client

from blossom.api.models import Source
from blossom.api.slack.transcription_check.messages import (
    _construct_transcription_check_text,
)
from blossom.utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)


def test_construct_transcription_check_text(client: Client) -> None:
    """Test that the fallback text is generated correctly."""
    client, _headers, user = setup_user_client(client, id=100, username="Userson")
    mod = create_user(id=200, username="Moddington")
    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        # Allow long line for URL
        # flake8: noqa: E501
        url="https://www.reddit.com/r/CuratedTumblr/comments/tirg5d/surviving_a_sitcom_death_mention/",
        source=Source(name="reddit"),
    )
    transcription = create_transcription(submission=submission, user=user)
    check = create_check(transcription, moderator=mod, trigger="Watched (100.0%)")

    expected = "Check for u/Userson (21 Γ) on r/CuratedTumblr | Watched (100.0%)"

    with patch(
        "blossom.authentication.models.BlossomUser.gamma_at_time", return_value=21
    ):
        actual = _construct_transcription_check_text(check)

    assert actual == expected
