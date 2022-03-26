from unittest.mock import MagicMock

import pytest

from api.slack import client as slack_client
from api.slack.commands import reset_cmd
from blossom.strings import translation
from utils.test_helpers import create_user

i18n = translation()


def test_process_coc_reset() -> None:
    """Test reset functionality and ensure that it works in reverse."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.accepted_coc is True
    message = f"reset {test_user.username}"

    # revoke their code of conduct acceptance
    reset_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.accepted_coc is False
    assert slack_client.chat_postMessage.call_args[1]["text"] == i18n["slack"][
        "reset_coc"
    ]["success"].format(test_user.username)

    # Now we approve them
    reset_cmd("", message)
    assert slack_client.chat_postMessage.call_count == 2
    test_user.refresh_from_db()
    assert test_user.accepted_coc is True
    assert slack_client.chat_postMessage.call_args[1]["text"] == i18n["slack"][
        "reset_coc"
    ]["success_undo"].format(test_user.username)


def test_process_coc_reset_with_slack_link() -> None:
    """Verify that messages with links in them are processed correctly."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.accepted_coc is True
    message = f"reset <https://reddit.com/example|{test_user.username}>"
    reset_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.accepted_coc is False


@pytest.mark.parametrize(
    "message,response",
    [
        ("reset", i18n["slack"]["errors"]["missing_username"]),
        (
            "reset asdf",
            i18n["slack"]["errors"]["unknown_username"].format(username="asdf"),
        ),
        ("reset a b c", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_coc_reset_errors(message: str, response: str) -> None:
    """Ensure that process_coc_reset errors when passed the wrong username."""
    slack_client.chat_postMessage = MagicMock()
    reset_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    assert slack_client.chat_postMessage.call_args[1]["text"] == response
