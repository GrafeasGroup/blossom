import json
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubmissionReport:
    """Tests validating the behavior of the Submission report process."""

    def test_report_already_removed(self, client: Client) -> None:
        """Verify that reporting an already removed submission doesn't do anything."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3, removed_from_queue=True)
        assert submission.removed_from_queue

        data = {"reason": "Violation of ALL the rules"}

        with patch("blossom.api.slack.client.chat_postMessage") as mock:
            result = client.patch(
                reverse("submission-report", args=[submission.id]),
                json.dumps(data),
                content_type="application/json",
                **headers
            )

            submission.refresh_from_db()

            assert result.status_code == status.HTTP_201_CREATED
            assert submission.removed_from_queue
            assert mock.call_count == 0

    def test_report_not_removed(self, client: Client) -> None:
        """Verify that reporting sends a message to Slack."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3)
        assert not submission.removed_from_queue
        assert not submission.report_reason
        assert not submission.report_slack_channel_id
        assert not submission.report_slack_message_ts

        data = {"reason": "Violation of ALL the rules"}

        with patch("blossom.api.slack.client.chat_postMessage"):
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
