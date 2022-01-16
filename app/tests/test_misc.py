from unittest.mock import MagicMock

from api.models import Source
from api.views.slack_helpers import client as slack_client
from app.views import ask_about_removing_post, get_blossom_app_source
from utils.test_helpers import create_submission


def test_get_blossom_app_source() -> None:
    """Verify that the TranscriptionApp source is created if needed."""
    Source.objects.all().delete()
    assert Source.objects.count() == 0

    response = get_blossom_app_source()
    assert Source.objects.count() == 1
    assert response.name == "TranscriptionApp"


def test_ask_about_removing_post() -> None:
    """Verify that block messages are handled appropriately."""
    # Mock the Slack client to catch the sent messages by the function under test.
    mock = MagicMock()
    mock.return_value = {
        "ok": True,
        "message": {"ts": "12345"},
        "channel": {"id": "6789"},
    }
    slack_client.chat_postMessage = mock

    submission = create_submission(id=3)
    assert not submission.report_slack_channel_id
    assert not submission.report_slack_message_ts

    ask_about_removing_post(submission, "asdf", worker_test_mode=True)
    submission.refresh_from_db()

    assert submission.report_slack_channel_id == "6789"
    assert submission.report_slack_message_ts == "12345"
    blocks = mock.call_args[1]["blocks"]
    assert "asdf" in blocks[2]["text"]["text"]
    assert "submission_3" in blocks[-1]["elements"][0]["value"]
    assert "submission_3" in blocks[-1]["elements"][1]["value"]
