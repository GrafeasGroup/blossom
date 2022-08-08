# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from typing import Dict, Optional

import pytest
from django.test import Client
from slack import WebClient

from blossom.api.models import Source, Submission
from blossom.api.slack.utils import (
    dict_to_table,
    extract_text_from_link,
    extract_url_from_link,
    get_reddit_username,
    get_source,
    parse_user,
)
from blossom.strings import translation
from blossom.utils.test_helpers import setup_user_client

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
    "text, username, found",
    [
        # No formatting
        ("user123", "user123", True),
        ("u/user123", "user123", True),
        ("/u/user123", "user123", True),
        # Link
        ("<https://reddit.com/u/user123|user123>", "user123", True),
        ("<https://reddit.com/u/user123|u/user123>", "user123", True),
        ("<https://reddit.com/u/user123|/u/user123>", "user123", True),
        # Bold
        ("*user123*", "user123", True),
        ("*u/user123*", "user123", True),
        ("*/u/user123*", "user123", True),
        # Link + Bold
        ("<https://reddit.com/u/user123|*user123*>", "user123", True),
        ("<https://reddit.com/u/user123|*u/user123*>", "user123", True),
        ("<https://reddit.com/u/user123|*/u/user123*>", "user123", True),
        ("*<https://reddit.com/u/user123|user123>*", "user123", True),
        ("*<https://reddit.com/u/user123|u/user123>*", "user123", True),
        ("*<https://reddit.com/u/user123|/u/user123>*", "user123", True),
        # Correct capitalization
        ("/u/USeR123", "user123", True),
        ("*usER123*", "user123", True),
        # Invalid username
        ("user456", "user456", False),
        ("*/u/user456*", "user456", False),
    ],
)
def test_parse_user(client: Client, text: str, username: str, found: bool) -> None:
    """Test that a username is parsed correctly."""
    client, headers, user = setup_user_client(client, id=100, username="user123")
    expected_user = user if found else None

    actual_user, actual_username = parse_user(text)

    assert actual_username == username
    assert actual_user == expected_user


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


@pytest.mark.parametrize(
    "submission, expected",
    [
        (
            Submission(
                url="https://reddit.com/r/assholedesign/comments/thrh7n/this_is_the_x_button_on_these_ads_literally_went/",
                source=Source(name="reddit"),
            ),
            "r/assholedesign",
        ),
        (
            Submission(url="https://example.com", source=Source(name="blossom")),
            "blossom",
        ),
        (
            Submission(url=None, source=Source(name="blossom")),
            "blossom",
        ),
    ],
)
def test_get_source(submission: Submission, expected: str) -> None:
    """Test that the source is extracted corrected from a submission."""
    actual = get_source(submission)
    assert actual == expected
