from unittest.mock import patch

import pytest

from blossom.api.slack.commands import blacklist_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import create_user

i18n = translation()


def test_process_blacklist() -> None:
    """Test blacklist functionality and ensure that it works in reverse."""
    test_user = create_user()
    assert test_user.blacklisted is False

    message = f"blacklist {test_user.username}"

    with patch("blossom.api.slack.commands.blacklist.client.chat_postMessage") as mock:
        blacklist_cmd("", message)
        test_user.refresh_from_db()

        assert test_user.blacklisted is True
        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == i18n["slack"]["blacklist"][
            "success"
        ].format(test_user.username)

    # Now we unblacklist them
    with patch("blossom.api.slack.commands.blacklist.client.chat_postMessage") as mock:
        blacklist_cmd("", message)
        test_user.refresh_from_db()

        assert test_user.blacklisted is False
        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == i18n["slack"]["blacklist"][
            "success_undo"
        ].format(test_user.username)


def test_process_blacklist_with_slack_link() -> None:
    """Verify that messages with links in them are processed correctly."""
    test_user = create_user()
    assert test_user.blacklisted is False

    message = f"blacklist <https://reddit.com/example|{test_user.username}>"

    with patch("blossom.api.slack.commands.blacklist.client.chat_postMessage"):
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
    with patch("blossom.api.slack.commands.blacklist.client.chat_postMessage") as mock:
        blacklist_cmd({}, message)

        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == response
