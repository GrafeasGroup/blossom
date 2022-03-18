# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from typing import Dict, Optional
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from django.test import Client
from slack import WebClient

from api.slack import client as slack_client
from api.slack.utils import (
    dict_to_table,
    extract_text_from_link,
    extract_url_from_link,
    get_reddit_username,
    send_transcription_check,
)
from blossom.strings import translation
from utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)

i18n = translation()


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


@pytest.mark.parametrize(
    "gamma, tr_url, reason, message",
    [
        (
            1,
            "url_stuff",
            "Low Activity",
            "*Transcription check* for u/TESTosterone (1 Γ):\n"
            "<foo|ToR Post> | <bar|Partner Post> | <url_stuff|Transcription>\n"
            "Reason: Low Activity\n"
            ":rotating_light: First transcription! :rotating_light:",
        ),
        (
            10,
            "url_stuff",
            "Watched (70.0%)",
            "*Transcription check* for u/TESTosterone (10 Γ):\n"
            "<foo|ToR Post> | <bar|Partner Post> | <url_stuff|Transcription>\n"
            "Reason: Watched (70.0%)",
        ),
        (
            20300,
            None,
            "Automatic (0.5%)",
            "*Transcription check* for u/TESTosterone (20,300 Γ):\n"
            "<foo|ToR Post> | <bar|Partner Post> | [Removed]\n"
            "Reason: Automatic (0.5%)",
        ),
    ],
)
def test_send_transcription_to_slack(
    client: Client, gamma: int, tr_url: str, reason: str, message: str,
) -> None:
    """Test the transcription check message."""
    # Patch a bunch of properties to get consistent output
    with patch(
        "authentication.models.BlossomUser.gamma",
        new_callable=PropertyMock,
        return_value=gamma,
    ), patch("api.slack.client.chat_postMessage", new_callable=MagicMock) as mock:
        client, headers, user = setup_user_client(client, username="TESTosterone")
        submission = create_submission(tor_url="foo", url="bar", claimed_by=user)
        transcription = create_transcription(submission, user, url=tr_url)

        send_transcription_check(transcription, submission, user, slack_client, reason)

        actual_message = mock.call_args[1]["text"]
        assert actual_message == message


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Normal text", "Normal text"),
        (
            "<https://www.reddit.com/user/transcribersofreddit|u/transcribersofreddit>",
            "u/transcribersofreddit",
        ),
        (
            "<https://www.reddit.com/user/transcribersofreddit>",
            "https://www.reddit.com/user/transcribersofreddit",
        ),
    ],
)
def test_extract_text_from_link(text: str, expected: str) -> None:
    """Test that the text is extracted from a Slack link."""
    actual = extract_text_from_link(text)
    assert actual == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Normal text", "Normal text"),
        (
            "<https://www.reddit.com/user/transcribersofreddit|u/transcribersofreddit>",
            "https://www.reddit.com/user/transcribersofreddit",
        ),
        (
            "<https://www.reddit.com/user/transcribersofreddit>",
            "https://www.reddit.com/user/transcribersofreddit",
        ),
        (
            "<https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/|Tor Post>",
            "https://reddit.com/r/TranscribersOfReddit/comments/t31715/curatedtumblr_image_linguistics_fax/",
        ),
    ],
)
def test_extract_url_from_link(text: str, expected: str) -> None:
    """Test that the URL is extracted from a Slack link."""
    actual = extract_url_from_link(text)
    assert actual == expected


@pytest.mark.parametrize(
    "user_obj,expected",
    [
        (
            {
                "avatar_hash": "ge3b51ca72de",
                "status_text": "Print is dead",
                "status_emoji": ":books:",
                "status_expiration": 0,
                "real_name": "Test Test",
                "display_name": "test123",
                "real_name_normalized": "Test Test",
                "display_name_normalized": "test123",
                "email": "test@example.org",
                "image_24": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_32": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_48": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_72": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_192": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_512": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "team": "T012AB3C4",
                "fields": {"Xf036MPXHAJJ": {"value": "test456"}},
            },
            "test456",
        ),
        (
            {
                "avatar_hash": "ge3b51ca72de",
                "status_text": "Print is dead",
                "status_emoji": ":books:",
                "status_expiration": 0,
                "real_name": "Test Test",
                "display_name": "test123",
                "real_name_normalized": "Test Test",
                "display_name_normalized": "test123",
                "email": "test@example.org",
                "image_24": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_32": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_48": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_72": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_192": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_512": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "team": "T012AB3C4",
                "fields": {"Xf036MPXHAJJ": {"value": "/u/test456"}},
            },
            "test456",
        ),
        (
            {
                "avatar_hash": "ge3b51ca72de",
                "status_text": "Print is dead",
                "status_emoji": ":books:",
                "status_expiration": 0,
                "real_name": "Test Test",
                "display_name": "test123",
                "real_name_normalized": "Test Test",
                "display_name_normalized": "test123",
                "email": "test@example.org",
                "image_24": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_32": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_48": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_72": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_192": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "image_512": "https://.../avatar/e3b51ca72dee4ef87916ae2b9240df50.jpg",
                "team": "T012AB3C4",
            },
            "test123",
        ),
    ],
)
def test_get_reddit_username(user_obj: Dict, expected: Optional[str]) -> None:
    """Test that the Reddit username is properly extracted."""

    class TestClient(WebClient):
        def users_profile_get(self, user: str):
            return {"ok": True, "profile": user_obj}

    client = TestClient()
    actual = get_reddit_username(client, {})

    assert actual == expected
