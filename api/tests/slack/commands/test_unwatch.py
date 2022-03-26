from unittest.mock import MagicMock

import pytest

from api.slack import client as slack_client
from api.slack.commands import unwatch_cmd
from blossom.strings import translation
from utils.test_helpers import create_user

i18n = translation()


def test_process_unwatch() -> None:
    """Test unwatch functionality."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123", overwrite_check_percentage=0.5)
    assert test_user.overwrite_check_percentage == 0.5
    # process the message
    unwatch_cmd("", "unwatch u123")
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    expected_message = i18n["slack"]["unwatch"]["success"].format(
        user=test_user.username
    )

    assert test_user.overwrite_check_percentage is None
    assert slack_client.chat_postMessage.call_args[1]["text"] == expected_message


@pytest.mark.parametrize(
    "message,response",
    [
        ("unwatch", i18n["slack"]["errors"]["missing_username"]),
        ("unwatch u123 50", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_unwatch_error(message: str, response: str) -> None:
    """Test watch command for invalid messages."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123")
    assert test_user.overwrite_check_percentage is None
    # process the message
    unwatch_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()

    assert test_user.overwrite_check_percentage is None
    assert slack_client.chat_postMessage.call_args[1]["text"] == response
