from unittest.mock import patch

import pytest

from blossom.api.slack.commands import unwatch_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import create_user

i18n = translation()


def test_process_unwatch() -> None:
    """Test unwatch functionality."""
    test_user = create_user(username="u123", overwrite_check_percentage=0.5)
    assert test_user.overwrite_check_percentage == 0.5

    expected_message = i18n["slack"]["unwatch"]["success"].format(
        user=test_user.username
    )

    # process the message
    with patch("blossom.api.slack.commands.unwatch.client.chat_postMessage") as mock:
        unwatch_cmd("", "unwatch u123")
        test_user.refresh_from_db()

        assert mock.call_count == 1
        assert test_user.overwrite_check_percentage is None
        assert mock.call_args[1]["text"] == expected_message


@pytest.mark.parametrize(
    "message,response",
    [
        ("unwatch", i18n["slack"]["errors"]["missing_username"]),
        ("unwatch u123 50", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_unwatch_error(message: str, response: str) -> None:
    """Test watch command for invalid messages."""
    test_user = create_user(username="u123")
    assert test_user.overwrite_check_percentage is None

    # process the message
    with patch("blossom.api.slack.commands.unwatch.client.chat_postMessage") as mock:
        unwatch_cmd("", message)
        test_user.refresh_from_db()

        assert mock.call_count == 1
        assert test_user.overwrite_check_percentage is None
        assert mock.call_args[1]["text"] == response
