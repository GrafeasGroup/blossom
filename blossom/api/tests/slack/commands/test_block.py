from unittest.mock import patch

import pytest

from blossom.api.slack.commands import block_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import create_user

i18n = translation()


def test_process_block() -> None:
    """Test block functionality and ensure that it works in reverse."""
    test_user = create_user()
    assert test_user.blocked is False

    message = f"block {test_user.username}"

    with patch("blossom.api.slack.commands.block.client.chat_postMessage") as mock:
        block_cmd("", message)
        test_user.refresh_from_db()

        assert test_user.blocked is True
        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == i18n["slack"]["block"]["success"].format(
            test_user.username
        )

    # Now we unblock them
    with patch("blossom.api.slack.commands.block.client.chat_postMessage") as mock:
        block_cmd("", message)
        test_user.refresh_from_db()

        assert test_user.blocked is False
        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == i18n["slack"]["block"][
            "success_undo"
        ].format(test_user.username)


def test_process_block_with_slack_link() -> None:
    """Verify that messages with links in them are processed correctly."""
    test_user = create_user()
    assert test_user.blocked is False

    message = f"block <https://reddit.com/example|{test_user.username}>"

    with patch("blossom.api.slack.commands.block.client.chat_postMessage"):
        block_cmd("", message)
        test_user.refresh_from_db()
        assert test_user.blocked is True


@pytest.mark.parametrize(
    "message,response",
    [
        ("block", i18n["slack"]["errors"]["missing_username"]),
        (
            "block asdf",
            i18n["slack"]["errors"]["unknown_username"].format(username="asdf"),
        ),
        ("a b c", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_block_errors(message: str, response: str) -> None:
    """Ensure that process_block errors when passed the wrong username."""
    with patch("blossom.api.slack.commands.block.client.chat_postMessage") as mock:
        block_cmd({}, message)

        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == response
