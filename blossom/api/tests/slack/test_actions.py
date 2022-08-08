import binascii
import hashlib
import hmac
import json
import time
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, RequestFactory
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper

from blossom.api.slack import client as slack_client
from blossom.api.slack.actions import is_valid_github_request, process_action
from blossom.api.views.slack import github_sponsors_endpoint

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


def test_process_action_check() -> None:
    """Test that a check action is routed correctly."""
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [{"name": "Approve", "value": "check_approved_1", "type": "button"}],
        "user": {"id": "U045VRZFT", "name": "Modulo"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.actions.process_check_action", return_value=None
    ) as check_mock, patch(
        "blossom.api.slack.actions.process_submission_report_update"
    ) as report_mock, patch(
        "blossom.api.slack.actions.client.chat_postMessage"
    ) as message_mock:
        process_action(data)

        assert check_mock.call_count == 1
        assert report_mock.call_count == 0
        assert message_mock.call_count == 0


def test_process_action_report() -> None:
    """Test that a report action is routed correctly."""
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [
            {"name": "Approve", "value": "approve_submission_3", "type": "button"}
        ],
        "user": {"id": "U045VRZFT", "name": "Modulo"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.actions.process_check_action", return_value=None
    ) as check_mock, patch(
        "blossom.api.slack.actions.process_submission_report_update"
    ) as report_mock, patch(
        "blossom.api.slack.actions.client.chat_postMessage"
    ) as message_mock:
        process_action(data)

        assert check_mock.call_count == 0
        assert report_mock.call_count == 1
        assert message_mock.call_count == 0


def test_process_action_unknown() -> None:
    """Test that an error message is sent for an unknown action."""
    data = {
        "channel": {"id": "C065W1189", "name": "forgotten-works"},
        "actions": [{"name": "Approve", "value": "asdas", "type": "button"}],
        "user": {"id": "U045VRZFT", "name": "Modulo"},
        "message_ts": "1458170866.000004",
    }

    with patch(
        "blossom.api.slack.actions.process_check_action", return_value=None
    ) as check_mock, patch(
        "blossom.api.slack.actions.process_submission_report_update"
    ) as report_mock, patch(
        "blossom.api.slack.actions.client.chat_postMessage"
    ) as message_mock:
        process_action(data)

        assert check_mock.call_count == 0
        assert report_mock.call_count == 0
        assert message_mock.call_count == 1
