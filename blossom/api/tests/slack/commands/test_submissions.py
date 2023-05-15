import zoneinfo
from datetime import date, datetime
from unittest.mock import patch

from django.test import Client

from blossom.api.models import Submission
from blossom.api.slack.commands.list_submissions import (
    _build_message,
    _build_raw_text_message,
    _build_response_blocks,
    fmt_date,
    process_submission_list,
    submissions_cmd,
)
from blossom.strings import translation
from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)

i18n = translation()


def test_fmt_date() -> None:
    test_date = date(year=2023, month=5, day=14)
    assert fmt_date(test_date) == "2023-05-14"

    test_datetime = datetime(year=2023, month=5, day=14, hour=8, minute=10)
    assert fmt_date(test_datetime) == "2023-05-14"


def test_build_message() -> None:
    """Just verify that the message builds correctly."""
    resp = _build_message()
    resp.validate_json()
    resp.to_dict()


def test_build_response_blocks_fallback() -> None:
    test_date = datetime(
        year=2023, month=5, day=14, hour=8, minute=10, tzinfo=zoneinfo.ZoneInfo("UTC")
    )
    user = create_user(username="BonzyTh3Clown")
    create_submission(completed_by=user, complete_time=test_date)

    resp = _build_response_blocks(Submission.objects.all(), user, test_date, test_date)
    assert len(resp) == 3
    assert (
        resp[0].text.text == "Transcriptions by *BonzyTh3Clown* from *2023-05-14* to *2023-05-14*:"
    )
    assert resp[2].text.text == "*2023-05-14* Dummy Submission"


def test_build_response_blocks() -> None:
    test_date = datetime(
        year=2023, month=5, day=14, hour=8, minute=10, tzinfo=zoneinfo.ZoneInfo("UTC")
    )
    user = create_user()
    create_submission(
        completed_by=user, complete_time=test_date, tor_url="https://grafeas.org", title="WAAA"
    )

    resp = _build_response_blocks(Submission.objects.all(), user, test_date, test_date)
    assert len(resp) == 3
    assert resp[2].text.text == "*2023-05-14* unit_tests | WAAA"


def test_too_many_blocks() -> None:
    for _ in range(50):
        create_submission(title=_)

    user = create_user()
    test_date = datetime(year=2023, month=5, day=14, tzinfo=zoneinfo.ZoneInfo("UTC"))
    assert _build_response_blocks(Submission.objects.all(), user, test_date, test_date) == []


def test_raw_text_message() -> None:
    test_date = datetime(year=2023, month=5, day=14, tzinfo=zoneinfo.ZoneInfo("UTC"))
    user = create_user()
    create_submission(
        completed_by=user, complete_time=test_date, tor_url="https://grafeas.org", title="WAAA"
    )

    resp = _build_raw_text_message(Submission.objects.all(), user, test_date, test_date)
    assert "Too many submissions" in resp
    assert "*2023-05-14* unit_tests | WAAA | <https://grafeas.org|ToR Post>" in resp


TEST_DATA = {
    "view": {
        "state": {
            "values": {
                "username": {"username_input": {"value": "BonzyTh3Clown"}},
                "date_start": {"select_start_date": {"value": "2022-01-01"}},
                "date_end": {"select_end_date": {"value": "2023-01-01"}},
            }
        },
        "response_urls": [{"channel_id": "0000"}],
    }
}


def test_process_submission_list_invalid_user() -> None:
    with patch("blossom.api.slack.commands.block.client.chat_postMessage") as mock:
        process_submission_list(TEST_DATA)

        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == i18n["slack"]["errors"]["unknown_username"].format(
            username="BonzyTh3Clown"
        )


def test_process_submission_list_no_submissions() -> None:
    create_user(username="BonzyTh3Clown")

    with patch("blossom.api.slack.commands.block.client.chat_postMessage") as mock:
        process_submission_list(TEST_DATA)
        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == i18n["slack"]["submissions"]["no_submissions"].format(
            username="BonzyTh3Clown", start="2022-01-01", end="2023-01-01"
        )
