from unittest.mock import patch

import pytest

from blossom.api.slack.commands import watchstatus_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import create_user

i18n = translation()


def test_process_watchstatus() -> None:
    """Test watchstatus functionality."""
    test_user = create_user(username="u123", overwrite_check_percentage=0.5)
    assert test_user.overwrite_check_percentage == 0.5

    expected_message = i18n["slack"]["watchstatus"]["success"].format(
        user=test_user.username, status="Watched (50.0%)"
    )

    # process the message
    with patch(
        "blossom.api.slack.commands.watchstatus.client.chat_postMessage"
    ) as mock:
        watchstatus_cmd("", "watchstatus u123")
        test_user.refresh_from_db()

        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == expected_message


@pytest.mark.parametrize(
    "message,response",
    [
        ("watchstatus", i18n["slack"]["errors"]["missing_username"]),
        ("watchstatus u123 50", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_watchstatus_error(message: str, response: str) -> None:
    """Test watch command for invalid messages."""
    test_user = create_user(username="u123")

    # process the message
    with patch(
        "blossom.api.slack.commands.watchstatus.client.chat_postMessage"
    ) as mock:
        watchstatus_cmd("", message)
        test_user.refresh_from_db()

        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == response
