# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from django.test import Client

from api.models import TranscriptionCheck
from api.slack import client as slack_client
from api.slack.commands import (
    blacklist_cmd,
    check_cmd,
    dadjoke_cmd,
    reset_cmd,
    unwatch_cmd,
    watch_cmd,
    watchlist_cmd,
    watchstatus_cmd,
)
from blossom.strings import translation
from utils.test_helpers import (
    create_check,
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)

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
    "message,expected",
    [
        (
            "watchlist",
            """*List of all watched users:*

```
100%: u/aaa
      u/bbb
 70%: u/fff
 60%: u/ccc
      u/eee
 30%: u/ddd
```""",
        ),
        (
            "watchlist percentage",
            """*List of all watched users:*

```
100%: u/aaa
      u/bbb
 70%: u/fff
 60%: u/ccc
      u/eee
 30%: u/ddd
```""",
        ),
        (
            "watchlist alphabetical",
            """*List of all watched users:*

```
u/aaa (100%)
u/bbb (100%)
u/ccc (60%)
u/ddd (30%)
u/eee (60%)
u/fff (70%)
```""",
        ),
        (
            "watchlist asdf",
            "Invalid sorting 'asdf'. Use either 'percentage' or 'alphabetical'.",
        ),
    ],
)
def test_process_watchlist(message: str, expected: str) -> None:
    """Test watchlist functionality."""
    slack_client.chat_postMessage = MagicMock()

    # Test users
    # The order is scrambled intentionally to test sorting
    create_user(id=888, username="hhh", overwrite_check_percentage=None)
    create_user(id=111, username="aaa", overwrite_check_percentage=1.0)
    create_user(id=444, username="ddd", overwrite_check_percentage=0.3)
    create_user(id=222, username="bbb", overwrite_check_percentage=1.0)
    create_user(id=777, username="ggg", overwrite_check_percentage=None)
    create_user(id=555, username="eee", overwrite_check_percentage=0.6)
    create_user(id=333, username="ccc", overwrite_check_percentage=0.6)
    create_user(id=666, username="fff", overwrite_check_percentage=0.7)

    # process the message
    watchlist_cmd("", message)
    slack_client.chat_postMessage.assert_called_once()
    assert slack_client.chat_postMessage.call_args[1]["text"] == expected


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


@pytest.mark.parametrize(
    "message", [("dadjoke"), ("dadjoke <@asdf>"), ("dadjoke a b c")],
)
def test_dadjoke_target(message: str) -> None:
    """Verify that dadjokes are delivered appropriately."""
    slack_client.chat_postMessage = MagicMock()

    dadjoke_cmd("", message, use_api=False)
    slack_client.chat_postMessage.assert_called_once()
    assert (
        i18n["slack"]["dadjoke"]["fallback_joke"]
        in slack_client.chat_postMessage.call_args[1]["text"]
    )
    if "<@" in message:
        # needs to be uppercased because otherwise slack will barf and
        # not parse it as a valid ping
        assert slack_client.chat_postMessage.call_args[1]["text"].startswith(
            "Hey <@ASDF>"
        )
    else:
        # no included username means don't use the ping formatting
        assert not slack_client.chat_postMessage.call_args[1]["text"].startswith("Hey")


@pytest.mark.parametrize(
    "url",
    [
        # Normal URLs
        "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
        "https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
        # Slack link
        "<https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/>",
        "<https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/>",
        "<https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/>",
        # Named Slack link
        "<https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/|Tor_Post>",
        "<https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/|Partner_Post>",
        "<https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/|Transcription>",
        # Wrong casing
        "https://reddit.com/r/transcribersofreddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/curatedtumblr/comments/t315gq/linguistics_fax/",
        "https://www.reddit.com/r/curatedtumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    ],
)
def test_check_cmd(client: Client, url: str) -> None:
    """Test that the check command generates a new check."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    )
    transcription = create_transcription(
        submission=submission,
        user=user,
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )

    with patch("api.slack.commands.client.chat_postMessage") as message_mock, patch(
        "api.slack.commands.send_check_message"
    ) as check_mock, patch("api.slack.commands.client.chat_getPermalink") as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 1
        assert link_mock.call_count == 1

        checks = TranscriptionCheck.objects.filter(transcription=transcription)
        assert len(checks) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
        "https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    ],
)
def test_check_cmd_existing_check(client: Client, url: str) -> None:
    """Test check command if a check already exists for the transcription."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    )
    transcription = create_transcription(
        submission=submission,
        user=user,
        url="https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )
    create_check(
        transcription=transcription, slack_channel_id="asd", slack_message_ts="1234"
    )

    checks = TranscriptionCheck.objects.filter(transcription=transcription)
    assert len(checks) == 1

    with patch("api.slack.commands.client.chat_postMessage") as message_mock, patch(
        "api.slack.commands.send_check_message"
    ) as check_mock, patch("api.slack.commands.client.chat_getPermalink") as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 0
        assert link_mock.call_count == 1

        checks = TranscriptionCheck.objects.filter(transcription=transcription)
        assert len(checks) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        "https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    ],
)
def test_check_cmd_no_transcription(client: Client, url: str) -> None:
    """Test check command if the submission does not have a transcription."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    create_submission(
        claimed_by=user,
        completed_by=user,
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    )

    with patch("api.slack.commands.client.chat_postMessage") as message_mock, patch(
        "api.slack.commands.send_check_message"
    ) as check_mock, patch("api.slack.commands.client.chat_getPermalink") as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 0
        assert link_mock.call_count == 0


@pytest.mark.parametrize(
    "url",
    [
        "asdf",
        "https://reddit.com/r/TranscribersOfReddit/comments/t31zvj/curatedtumblr_image_love_and_languages/",
        "https://reddit.com/r/CuratedTumblr/comments/t31xsx/love_and_languages/",
        "https://reddit.com/r/CuratedTumblr/comments/t31xsx/love_and_languages/hypsf0v/",
    ],
)
def test_check_cmd_unknown_url(client: Client, url: str) -> None:
    """Test check command if a check already exists for the transcription."""
    client, headers, user = setup_user_client(client, id=100, username="Userson")
    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        url="https://reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/",
    )
    transcription = create_transcription(
        submission=submission,
        user=user,
        url="https://www.reddit.com/r/CuratedTumblr/comments/t315gq/linguistics_fax/hypuw2r/",
    )
    create_check(
        transcription=transcription, slack_channel_id="asd", slack_message_ts="1234"
    )

    with patch("api.slack.commands.client.chat_postMessage") as message_mock, patch(
        "api.slack.commands.send_check_message"
    ) as check_mock, patch("api.slack.commands.client.chat_getPermalink") as link_mock:
        check_cmd("", f"check {url}")

        assert message_mock.call_count == 1
        assert check_mock.call_count == 0
        assert link_mock.call_count == 0
