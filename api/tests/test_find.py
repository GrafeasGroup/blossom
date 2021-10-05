# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from typing import Optional

import pytest

from api.views.find import normalize_url


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        (
            "https://www.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        (
            "https://www.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        (
            "https://new.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        (
            "https://old.reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
        (
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work",
            "https://reddit.com/r/TranscribersOfReddit/comments/q1tnhc/antiwork_image_work_is_work/",
        ),
    ],
)
def test_normalize_url(url: str, expected: Optional[str]) -> None:
    """Verify that the URL is normalized correctly."""
    actual = normalize_url(url)
    assert actual == expected
