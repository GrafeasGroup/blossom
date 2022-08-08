from unittest.mock import MagicMock

from blossom.api.models import Source
from blossom.api.slack import client as slack_client
from blossom.api.slack.actions import ask_about_removing_post
from blossom.app.views import get_blossom_app_source
from blossom.utils.test_helpers import create_submission


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
    # From https://api.slack.com/methods/chat.postMessage
    mock.return_value = {
        "ok": True,
        "channel": "C1H9RESGL",
        "ts": "1503435956.000247",
        "message": {
            "text": "Here's a message for you",
            "username": "ecto1",
            "bot_id": "B19LU7CSY",
            "attachments": [
                {
                    "text": "This is an attachment",
                    "id": 1,
                    "fallback": "This is an attachment's fallback",
                }
            ],
            "type": "message",
            "subtype": "bot_message",
            "ts": "1503435956.000247",
        },
    }
    slack_client.chat_postMessage = mock

    submission = create_submission(id=3)
    assert not submission.report_slack_channel_id
    assert not submission.report_slack_message_ts

    ask_about_removing_post(submission, "asdf", worker_test_mode=True)
    submission.refresh_from_db()

    assert submission.report_slack_channel_id == "C1H9RESGL"
    assert submission.report_slack_message_ts == "1503435956.000247"
    blocks = mock.call_args[1]["blocks"]
    assert "asdf" in blocks[0]["text"]["text"]
    assert "submission_3" in blocks[-1]["elements"][0]["value"]
    assert "submission_3" in blocks[-1]["elements"][1]["value"]
