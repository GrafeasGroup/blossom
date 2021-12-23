# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from typing import Optional

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.views.find import find_by_submission_url, normalize_url
from utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        # Correct URL
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        # HTTP
        (
            "http://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        # www prefix
        (
            "https://www.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        # new prefix
        (
            "https://new.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        # old prefix
        (
            "https://old.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        # missing slash
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        # Query parameters
        (
            "https://www.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/comment/hfgp86i/"
            + "?utm_source=share&utm_medium=web2x&context=3",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/comment/hfgp86i/",
        ),
    ],
)
def test_normalize_url(url: str, expected: Optional[str]) -> None:
    """Verify that the URL is normalized correctly."""
    actual = normalize_url(url)
    assert actual == expected


@pytest.mark.parametrize(
    "url,url_type,expected",
    [
        # Submission URL
        ("https://reddit.com/r/antiwork/comments/q1tlcf/work_is_work/", "url", True,),
        # ToR Submission URL
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "tor_url",
            True,
        ),
        # Other submission URL
        (
            "https://reddit.com/r/aaaaaaacccccccce/comments/q1t6kh/not_so_sure_about_the_demiboy_thing_anymore_im/",
            "url",
            False,
        ),
        # Other ToR URL
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1ucl3/aaaaaaacccccccce_image_not_so_sure_about_the/",
            "tor_url",
            False,
        ),
    ],
)
def test_find_by_submission_url(
    client: Client, url: str, url_type: str, expected: bool
) -> None:
    """Verify that a submission is found by its submission URL."""
    client, headers, user = setup_user_client(client, id=123, username="test_user")

    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        url="https://reddit.com/r/antiwork/comments/q1tlcf/work_is_work/",
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        content_url="https://i.redd.it/upwchc4bqhr71.jpg",
        title="Work is work",
    )

    transcription = create_transcription(
        submission=submission,
        user=user,
        url="https://reddit.com/r/antiwork/comments/q1tlcf/comment/hfgp814/",
    )

    actual = find_by_submission_url(url, url_type)

    if expected:
        assert actual["submission"] == submission
        assert actual["transcription"] == transcription
        assert actual["author"] == user
    else:
        assert actual is None


@pytest.mark.parametrize(
    "url,expected",
    [
        # Submission URL
        ("https://reddit.com/r/antiwork/comments/q1tlcf/work_is_work/", True),
        # ToR Submission URL
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            True,
        ),
        # Transcription URL
        ("https://reddit.com/r/antiwork/comments/q1tlcf/comment/hfgp814/", True),
        # Shared transcription URL
        (
            "https://www.reddit.com/r/antiwork/comments/q1tlcf/comment/hfgp814/"
            "?utm_source=share&utm_medium=web2x&context=3",
            True,
        ),
        # Other submission URL
        (
            "https://reddit.com/r/aaaaaaacccccccce/comments/q1t6kh/not_so_sure_about_the_demiboy_thing_anymore_im/",
            False,
        ),
        # Other ToR URL
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1ucl3/aaaaaaacccccccce_image_not_so_sure_about_the/",
            False,
        ),
        # Other Transcription URL
        (
            "https://reddit.com/r/NonPoliticalTwitter/comments/rn02rf/subtitles/hppsgrs/",
            False,
        ),
    ],
)
def test_find(client: Client, url: str, expected: bool) -> None:
    """Verify that the posts can be found by their URL."""
    client, headers, user = setup_user_client(client, id=123, username="test_user")

    submission = create_submission(
        claimed_by=user,
        completed_by=user,
        url="https://reddit.com/r/antiwork/comments/q1tlcf/work_is_work/",
        tor_url="https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        content_url="https://i.redd.it/upwchc4bqhr71.jpg",
        title="Work is work",
    )

    transcription = create_transcription(
        submission=submission,
        user=user,
        url="https://reddit.com/r/antiwork/comments/q1tlcf/comment/hfgp814/",
    )

    result = client.get(
        reverse("find") + f"?url={url}", content_type="application/json", **headers,
    )

    if expected:
        assert result.status_code == status.HTTP_200_OK
        actual = result.json()

        assert actual["submission"]["id"] == submission.id
        assert actual["transcription"]["id"] == transcription.id
        assert actual["author"]["id"] == user.id
    else:
        assert result.status_code == status.HTTP_404_NOT_FOUND
