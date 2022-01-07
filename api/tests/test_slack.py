import binascii
import hashlib
import hmac
import json
import time
from typing import Dict
from unittest.mock import MagicMock

import pytest
from django.test import Client
from django.test.client import RequestFactory
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper

from api.views.slack import github_sponsors_endpoint
from api.views.slack_helpers import client as slack_client
from api.views.slack_helpers import (
    dadjoke_target,
    dict_to_table,
    is_valid_github_request,
    process_blacklist,
    process_coc_reset,
    process_unwatch,
    process_watch,
)
from blossom.strings import translation
from utils.test_helpers import create_user

i18n = translation()

# TODO: There is a way to mock decorators, but I can't figure it out.
# There's a lot of testing that needs to happen for this module, but I can't
# get past the threading decorator and the patch calls don't seem to work.
# Resources:
# https://stackoverflow.com/questions/7667567/can-i-patch-a-python-decorator-before-it-wraps-a-function  # noqa: E501
# http://alexmarandon.com/articles/python_mock_gotchas/
# https://stackoverflow.com/questions/36812830/mocking-decorators-in-python-with-mock-and-pytest  # noqa: E501

# NOTE: In order to test slack, you must add the `settings` hook and set
# `settings.ENABLE_SLACK = True`. MAKE SURE that if you're writing a new
# test that uses ENABLE_SLACK that you patch `requests.post` or it will
# try and ping modchat (if you're running locally) or explode if this is
# running in the github actions pipeline.

SLACK_SIGNING_SECRET = "12345"


def get_slack_headers(body: dict, settings: SettingsWrapper) -> dict:
    """Mock the headers required by slack validation."""
    create_time = str(int(time.time()))

    body = json.dumps(body)
    sig_basestring = "v0:" + create_time + ":" + body
    signature = (
        "v0="
        + hmac.new(
            bytes(settings.SLACK_SIGNING_SECRET, "latin-1"),
            msg=bytes(sig_basestring, "latin-1"),
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    return {
        "HTTP_X-Slack-Signature": signature,
        "HTTP_X-Slack-Request-Timestamp": create_time,
    }


def test_challenge_request(client: Client, settings: SettingsWrapper) -> None:
    """Test handling of Slack's new endpoint challenge message."""
    settings.SLACK_SIGNING_SECRET = SLACK_SIGNING_SECRET
    data = {"challenge": "asdfasdfasdf"}
    headers = get_slack_headers(data, settings)
    result = client.post(
        reverse("slack"), json.dumps(data), content_type="application/json", **headers
    )
    assert result.content == b"asdfasdfasdf"


@pytest.mark.parametrize(
    "test_data",
    [
        {"data": {"aaa": "bbb"}, "signature": "nope", "result": False},
        {
            "data": {"bbb": "ccc"},
            "signature": "sha1=757fc3cb2f66db92a1d164c116358660e4e7656e",
            "result": True,
        },
        {"data": {"aaa": "bbb"}, "signature": "sha1=ttthhhbbbttt", "result": False},
        {"data": {"aaa": "bbb"}, "signature": None, "result": True},
    ],
)
def test_is_github_valid_request(
    rf: RequestFactory, settings: SettingsWrapper, test_data: Dict
) -> None:
    """Test to ensure that a webhook from GitHub Sponsors is valid."""
    request = rf.post(
        "slack/github/sponsors/",
        data=test_data["data"],
        content_type="application/json",
    )

    settings.GITHUB_SPONSORS_SECRET_KEY = "shhh, it's a secret"

    if not test_data["signature"]:
        test_data["signature"] = "sha1={}".format(
            binascii.hexlify(
                hmac.digest(
                    msg=request.body,
                    key=settings.GITHUB_SPONSORS_SECRET_KEY.encode(),
                    digest="sha1",
                )
            ).decode()
        )

    request.headers = {"x-hub-signature": test_data["signature"]}
    assert is_valid_github_request(request) is test_data["result"]


def test_github_missing_signature(rf: RequestFactory) -> None:
    """Test to ensure a request that is missing the signature is marked invalid."""
    """Test to ensure that a webhook from GitHub Sponsors is valid."""
    request = rf.post(
        "slack/github/sponsors/", data={"aaa": "bbb"}, content_type="application/json"
    )
    assert is_valid_github_request(request) is False


@pytest.mark.parametrize(
    "test_data",
    [
        {
            "username": "bob",
            "tier": "A",
            "action": "created",
            "result": ":tada: GitHub Sponsors: [created] - bob | A :tada:",
            "status_code": 200,
        },
        {
            "username": "bobbert",
            "tier": "B",
            "action": "cancelled",
            "result": ":sob: GitHub Sponsors: [cancelled] - bobbert | B :sob:",
            "status_code": 200,
        },
        {
            "username": "bobby",
            "tier": "C",
            "action": "edited",
            "result": (
                ":rotating_light: GitHub Sponsors: [edited] - bobby | C :rotating_light:"
            ),
            "status_code": 200,
        },
    ],
)
def test_github_sponsor_slack_message(
    rf: RequestFactory, settings: SettingsWrapper, test_data: Dict
) -> None:
    """Test to ensure webhooks from GitHub Sponsors trigger appropriate slack pings."""
    slack_client.chat_postMessage = MagicMock()
    request = rf.post(
        "slack/github/sponsors/",
        data={
            "action": test_data["action"],
            "sponsorship": {
                "sponsor": {"login": test_data["username"]},
                "tier": {"name": test_data["tier"]},
            },
        },
        content_type="application/json",
    )
    request.headers = {
        "x-hub-signature": "sha1={}".format(
            binascii.hexlify(
                hmac.digest(
                    msg=request.body,
                    key=settings.GITHUB_SPONSORS_SECRET_KEY.encode(),
                    digest="sha1",
                )
            ).decode()
        )
    }
    response = github_sponsors_endpoint(request)

    assert slack_client.chat_postMessage.call_args[1]["text"] == test_data["result"]
    assert response.status_code == test_data["status_code"]


@pytest.mark.parametrize(
    "test_data",
    [
        {
            "data": {
                "dictionary": {"a": 1, "b": 2},
                "titles": ["Pinky", "Brain"],
                "width": 20,
            },
            "result": [
                "Pinky                | Brain               ",
                "----------------------------------------",
                "a                    | 1                   ",
                "b                    | 2                   ",
            ],
        },
        {
            "data": {
                "dictionary": {"a": 1, "b": [1, 2, 3, 4, 5]},
                "titles": ["Pinky", "Brain"],
                "width": 20,
            },
            "result": [
                "Pinky                | Brain               ",
                "----------------------------------------",
                "a                    | 1                   ",
                "b                    | 1, 2, 3, 4, 5       ",
            ],
        },
        {
            "data": {
                "dictionary": {"a": None},
                "titles": ["Pinky", "Brain"],
                "width": 20,
            },
            "result": [
                "Pinky                | Brain               ",
                "----------------------------------------",
                "a                    | None                ",
            ],
        },
        {
            "data": {"dictionary": {"a": None}},  # noqa: E231
            "result": ["Key | Value", "------", "a   | None"],  # noqa: E231
        },
    ],
)
def test_slack_neat_printer(test_data: Dict) -> None:
    """Verify that the neat printer formats tables appropriately."""
    result = dict_to_table(**test_data["data"])
    assert result == test_data["result"]


def test_process_blacklist() -> None:
    """Test blacklist functionality and ensure that it works in reverse."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.blacklisted is False
    message = f"blacklist {test_user.username}"

    process_blacklist("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.blacklisted is True
    assert slack_client.chat_postMessage.call_args[1]["text"] == i18n["slack"][
        "blacklist"
    ]["success"].format(test_user.username)

    # Now we unblacklist them
    process_blacklist("", message)
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
    process_blacklist("", message)
    test_user.refresh_from_db()
    assert test_user.blacklisted is True


@pytest.mark.parametrize(
    "message,response",
    [
        ("blacklist", i18n["slack"]["errors"]["missing_username"]),
        ("blacklist asdf", i18n["slack"]["errors"]["unknown_username"]),
        ("a b c", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_blacklist_errors(message: str, response: str) -> None:
    """Ensure that process_blacklist errors when passed the wrong username."""
    slack_client.chat_postMessage = MagicMock()
    process_blacklist({}, message)
    slack_client.chat_postMessage.assert_called_once()
    assert slack_client.chat_postMessage.call_args[1]["text"] == response


def test_process_coc_reset() -> None:
    """Test reset functionality and ensure that it works in reverse."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.accepted_coc is True
    message = f"reset {test_user.username}"

    # revoke their code of conduct acceptance
    process_coc_reset("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.accepted_coc is False
    assert slack_client.chat_postMessage.call_args[1]["text"] == i18n["slack"][
        "reset_coc"
    ]["success"].format(test_user.username)

    # Now we approve them
    process_coc_reset("", message)
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
    process_coc_reset("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.accepted_coc is False


@pytest.mark.parametrize(
    "message,response",
    [
        ("reset", i18n["slack"]["errors"]["missing_username"]),
        ("reset asdf", i18n["slack"]["errors"]["unknown_username"]),
        ("reset a b c", i18n["slack"]["errors"]["too_many_params"]),
    ],
)
def test_process_coc_reset_errors(message: str, response: str) -> None:
    """Ensure that process_coc_reset errors when passed the wrong username."""
    slack_client.chat_postMessage = MagicMock()
    process_coc_reset("", message)
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
    # process the message
    process_watch("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    expected_message = i18n["slack"]["watch"]["success"].format(
        user=test_user.username, percentage=percentage * 100
    )

    assert test_user.overwrite_check_percentage == percentage
    assert slack_client.chat_postMessage.call_args[1]["text"] == expected_message


@pytest.mark.parametrize(
    "message,response",
    [
        ("watch", i18n["slack"]["errors"]["missing_username"]),
        ("watch u123 50 13", i18n["slack"]["errors"]["too_many_params"]),
        ("watch u456 50", i18n["slack"]["errors"]["unknown_username"]),
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
    ],
)
def test_process_watch_error(message: str, response: str) -> None:
    """Test watch command for invalid messages."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user(username="u123")
    assert test_user.overwrite_check_percentage is None
    # process the message
    process_watch("", message)
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
    process_unwatch("", "unwatch u123")
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
    process_unwatch("", message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()

    assert test_user.overwrite_check_percentage is None
    assert slack_client.chat_postMessage.call_args[1]["text"] == response


@pytest.mark.parametrize(
    "message", [("dadjoke"), ("dadjoke <@asdf>"), ("dadjoke a b c")],
)
def test_dadjoke_target(message: str) -> None:
    """Verify that dadjokes are delivered appropriately."""
    slack_client.chat_postMessage = MagicMock()

    dadjoke_target("", message, use_api=False)
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
