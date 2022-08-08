from unittest.mock import patch

import pytest

from blossom.api.slack.commands import reset_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import create_user

i18n = translation()


def test_process_coc_reset() -> None:
    """Test reset functionality and ensure that it works in reverse."""
    test_user = create_user()
    assert test_user.accepted_coc is True
    message = f"reset {test_user.username}"

    # revoke their code of conduct acceptance
    with patch("blossom.api.slack.commands.reset.client.chat_postMessage") as mock:
        reset_cmd("", message)
        test_user.refresh_from_db()

        assert mock.call_count == 1
        assert test_user.accepted_coc is False
        assert mock.call_args[1]["text"] == i18n["slack"]["reset_coc"][
            "success"
        ].format(test_user.username)

    # Now we approve them
    with patch("blossom.api.slack.commands.reset.client.chat_postMessage") as mock:
        reset_cmd("", message)
        test_user.refresh_from_db()

        assert mock.call_count == 1
        assert test_user.accepted_coc is True
        assert mock.call_args[1]["text"] == i18n["slack"]["reset_coc"][
            "success_undo"
        ].format(test_user.username)


def test_process_coc_reset_with_slack_link() -> None:
    """Verify that messages with links in them are processed correctly."""
    test_user = create_user()
    assert test_user.accepted_coc is True

    message = f"reset <https://reddit.com/example|{test_user.username}>"

    with patch("blossom.api.slack.commands.reset.client.chat_postMessage") as mock:
        reset_cmd("", message)
        test_user.refresh_from_db()

        assert mock.call_count == 1
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
    with patch("blossom.api.slack.commands.reset.client.chat_postMessage") as mock:
        reset_cmd("", message)

        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == response
