from unittest.mock import MagicMock

import pytest

from api.slack import client as slack_client
from api.slack.commands import watchstatus_cmd
from blossom.strings import translation
from utils.test_helpers import create_user

i18n = translation()


def test_process_watchstatus() -> None:
    """Test watchstatus functionality."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123", overwrite_check_percentage=0.5)
    assert test_user.overwrite_check_percentage == 0.5

    # process the message
    watchstatus_cmd("", "watchstatus u123")
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    expected_message = i18n["slack"]["watchstatus"]["success"].format(
        user=test_user.username, status="Watched (50.0%)"
    )

    assert slack_client.chat_postMessage.call_args[1]["text"] == expected_message


@pytest.mark.parametrize(
    "message,response",
    [
        ("watchstatus", i18n["slack"]["errors"]["missing_username"]),
        ("watchstatus u123 50", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_watchstatus_error(message: str, response: str) -> None:
    """Test watch command for invalid messages."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123")

    # process the message
    watchstatus_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()

    assert slack_client.chat_postMessage.call_args[1]["text"] == response
