from unittest.mock import MagicMock

import pytest

from api.slack import client as slack_client
from api.slack.commands import blacklist_cmd
from blossom.strings import translation
from utils.test_helpers import create_user

i18n = translation()


def test_process_blacklist() -> None:
    """Test blacklist functionality and ensure that it works in reverse."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.blacklisted is False
    message = f"blacklist {test_user.username}"

    blacklist_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.blacklisted is True
    assert slack_client.chat_postMessage.call_args[1]["text"] == i18n["slack"][
        "blacklist"
    ]["success"].format(test_user.username)

    # Now we unblacklist them
    blacklist_cmd("", message)
    assert slack_client.chat_postMessage.call_count == 2
    test_user.refresh_from_db()
    assert test_user.blacklisted is False
    assert slack_client.chat_postMessage.call_args[1]["text"] == i18n["slack"][
        "blacklist"
    ]["success_undo"].format(test_user.username)


def test_process_blacklist_with_slack_link() -> None:
    """Verify that messages with links in them are processed correctly."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.blacklisted is False
    message = f"blacklist <https://reddit.com/example|{test_user.username}>"
    blacklist_cmd("", message)
    test_user.refresh_from_db()
    assert test_user.blacklisted is True


@pytest.mark.parametrize(
    "message,response",
    [
        ("blacklist", i18n["slack"]["errors"]["missing_username"]),
        (
            "blacklist asdf",
            i18n["slack"]["errors"]["unknown_username"].format(username="asdf"),
        ),
        ("a b c", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_blacklist_errors(message: str, response: str) -> None:
    """Ensure that process_blacklist errors when passed the wrong username."""
    slack_client.chat_postMessage = MagicMock()
    blacklist_cmd({}, message)
    slack_client.chat_postMessage.assert_called_once()
    assert slack_client.chat_postMessage.call_args[1]["text"] == response
