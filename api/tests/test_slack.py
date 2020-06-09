import binascii
import hmac
import json
from typing import Dict
from unittest.mock import MagicMock

import pytest
from django.test import Client
from django.test.client import RequestFactory
from django_hosts.resolvers import reverse
from pytest_django.fixtures import SettingsWrapper

from api.slack_views import github_sponsors_endpoint
from api.slack_helpers import client as slack_client
from api.slack_helpers import is_valid_github_request, neat_printer, process_blacklist
from api.tests.helpers import create_user
from blossom.strings import translation

i18n = translation()


# TODO: There is a way to mock decorators, but I can't figure it out.
# There's a lot of testing that needs to happen for this module, but I can't
# get past the threading decorator and the patch calls don't seem to work.
# Resources:
# https://stackoverflow.com/questions/7667567/can-i-patch-a-python-decorator-before-it-wraps-a-function  # noqa: E501
# http://alexmarandon.com/articles/python_mock_gotchas/
# https://stackoverflow.com/questions/36812830/mocking-decorators-in-python-with-mock-and-pytest  # noqa: E501


def test_challenge_request(client: Client) -> None:
    """Test handling of Slack's new endpoint challenge message."""
    data = {"challenge": "asdfasdfasdf"}
    result = client.post(
        reverse("slack", host="api"),
        json.dumps(data),
        HTTP_HOST="api",
        content_type="application/json",
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
        HTTP_HOST="api",
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
    """Test to ensure a request that is missing the signature is marked invalid"""
    """Test to ensure that a webhook from GitHub Sponsors is valid."""
    request = rf.post(
        "slack/github/sponsors/",
        data={"aaa": "bbb"},
        content_type="application/json",
        HTTP_HOST="api",
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
        HTTP_HOST="api",
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
                "dictionary": {
                    'a': 1, 'b': 2
                },
                "titles": [
                    "Pinky",
                    "Brain"
                ],
                "width": 20
            },
            "result": [
                'Pinky                | Brain               ',
                '----------------------------------------',
                'a                    | 1                   ',
                'b                    | 2                   '
            ]
        },
        {
            "data": {
                "dictionary": {'a': 1, 'b': [1, 2, 3, 4, 5]},
                "titles": ['Pinky', 'Brain'],
                "width": 20
            },
            "result": [
                'Pinky                | Brain               ',
                '----------------------------------------',
                'a                    | 1                   ',
                'b                    | 1, 2, 3, 4, 5       '
            ]
        },
        {
            "data": {
                "dictionary": {'a': None},
                "titles": ['Pinky', 'Brain'],
                "width": 20
            },
            "result": [
                'Pinky                | Brain               ',
                '----------------------------------------',
                'a                    | None                '
            ]
        }
    ],
)
def test_slack_neat_printer(test_data: Dict):
    """Verify that the neat printer formats tables appropriately."""
    result = neat_printer(**test_data["data"])
    assert result == test_data["result"]


def test_process_blacklist():
    """Test blacklist functionality and ensure that it works in reverse."""
    slack_client.chat_postMessage = MagicMock()

    test_user = create_user()
    assert test_user.blacklisted is False
    message = f"blacklist {test_user.username}"

    process_blacklist({}, message)
    slack_client.chat_postMessage.assert_called_once()
    test_user.refresh_from_db()
    assert test_user.blacklisted is True
    assert slack_client.chat_postMessage.call_args[1]["text"] == \
           i18n["slack"]["blacklist"]["success"].format(test_user.username)

    # Now we unblacklist them
    process_blacklist({}, message)
    assert slack_client.chat_postMessage.call_count == 2
    test_user.refresh_from_db()
    assert test_user.blacklisted is False
    assert slack_client.chat_postMessage.call_args[1]["text"] == \
           i18n["slack"]["blacklist"]["success_undo"].format(test_user.username)


@pytest.mark.parametrize(
    "message,response",
    [
        ("blacklist", i18n["slack"]["blacklist"]["missing_username"]),
        ("blacklist asdf", i18n["slack"]["blacklist"]["unknown_username"]),
        ("a b c", i18n["slack"]["too_many_params"])
    ],
)
def test_process_blacklist_errors(message, response):
    """Ensure that process_blacklist errors when passed the wrong username."""
    slack_client.chat_postMessage = MagicMock()
    process_blacklist({}, message)
    slack_client.chat_postMessage.assert_called_once()
    assert slack_client.chat_postMessage.call_args[1]["text"] == response
