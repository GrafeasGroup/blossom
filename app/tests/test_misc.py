from unittest.mock import MagicMock

from django.test import RequestFactory

from api.models import Source
from api.views.slack_helpers import client as slack_client
from app.views import ask_about_removing_post, get_blossom_app_source


def test_get_blossom_app_source() -> None:
    """Verify that the TranscriptionApp source is created if needed."""
    Source.objects.all().delete()
    assert Source.objects.count() == 0

    response = get_blossom_app_source()
    assert Source.objects.count() == 1
    assert response.name == "TranscriptionApp"


def test_ask_about_removing_post(rf: RequestFactory) -> None:
    """Verify that block messages are handled appropriately."""
    # Mock the Slack client to catch the sent messages by the function under test.
    slack_client.chat_postMessage = MagicMock()
    request = rf.get("slack/github/sponsors/", content_type="application/json",)

    submission = "a"
    print(ask_about_removing_post(request, submission))
