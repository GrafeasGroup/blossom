import json
from unittest.mock import MagicMock

from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.views.slack_helpers import client as slack_client
from utils.test_helpers import create_submission, setup_user_client


class TestSubmissionReport:
    """Tests validating the behavior of the Submission report process."""

    def test_report_already_removed(self, client: Client) -> None:
        """Verify that reporting an already removed submission doesn't do anything."""
        slack_client.chat_postMessage = MagicMock()
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3, removed_from_queue=True)
        assert submission.removed_from_queue

        data = {"reason": "Violation of ALL the rules"}

        result = client.patch(
            reverse("submission-report", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_201_CREATED
        assert submission.removed_from_queue
        assert slack_client.chat_postMessage.call_count == 0

    def test_report_not_removed(self, client: Client) -> None:
        """Verify that reporting sends a message to Slack."""
        mock = MagicMock()
        slack_client.chat_postMessage = mock
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3)
        assert not submission.removed_from_queue
        assert not submission.report_reason
        assert not submission.report_slack_id

        data = {"reason": "Violation of ALL the rules"}

        result = client.patch(
            reverse("submission-report", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_201_CREATED
        assert not submission.removed_from_queue
        assert submission.report_reason == "Violation of ALL the rules"
