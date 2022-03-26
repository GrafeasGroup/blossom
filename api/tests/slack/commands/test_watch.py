from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from api.slack import client as slack_client
from api.slack.commands import watch_cmd
from blossom.strings import translation
from utils.test_helpers import create_user

i18n = translation()


@pytest.mark.parametrize(
    "message,percentage",
    [
        ("watch u123", 1),
        ("watch u123 50", 0.5),
        ("watch u123 75%", 0.75),
        ("watch <https://reddit.com/u/u123|u123> 10", 0.1),
    ],
)
def test_process_watch(message: str, percentage: float) -> None:
    """Test watch functionality."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123")
    assert test_user.overwrite_check_percentage is None

    # Make sure that the overwrite is allowed
    with patch(
        "authentication.models.BlossomUser.auto_check_percentage",
        new_callable=PropertyMock,
        return_value=0.05,
    ):
        # process the message
        watch_cmd("", message)
        slack_client.chat_postMessage.assert_called_once()
        test_user.refresh_from_db()
        expected_message = i18n["slack"]["watch"]["success"].format(
            user=test_user.username, percentage=percentage, previous="Automatic (5.0%)"
        )

        assert test_user.overwrite_check_percentage == percentage
        assert slack_client.chat_postMessage.call_args[1]["text"] == expected_message


@pytest.mark.parametrize(
    "message,response",
    [
        ("watch", i18n["slack"]["errors"]["missing_username"]),
        ("watch u123 50 13", i18n["slack"]["errors"]["too_many_params"]),
        (
            "watch u456 50",
            i18n["slack"]["errors"]["unknown_username"].format(username="u456"),
        ),
        (
            "watch u123 -1",
            i18n["slack"]["watch"]["invalid_percentage"].format(percentage="-1"),
        ),
        (
            "watch u123 101",
            i18n["slack"]["watch"]["invalid_percentage"].format(percentage="101"),
        ),
        (
            "watch u123 0.5",
            i18n["slack"]["watch"]["invalid_percentage"].format(percentage="0.5"),
        ),
        (
            "watch u123 50",
            i18n["slack"]["watch"]["percentage_too_low"].format(auto_percentage=0.7),
        ),
    ],
)
def test_process_watch_error(message: str, response: str) -> None:
    """Test watch command for invalid messages."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123")
    assert test_user.overwrite_check_percentage is None

    with patch(
        "authentication.models.BlossomUser.auto_check_percentage",
        new_callable=PropertyMock,
        return_value=0.7,
    ):
        # process the message
        watch_cmd("", message)
        slack_client.chat_postMessage.assert_called_once()
        test_user.refresh_from_db()

        assert test_user.overwrite_check_percentage is None
        assert slack_client.chat_postMessage.call_args[1]["text"] == response
