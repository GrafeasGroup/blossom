import json
from uuid import uuid4

from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.api.models import Submission, Transcription
from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)


class TestSubmissionYeet:
    """Tests validating the behavior of the Submission yeetal process."""

    def test_yeet(self, client: Client) -> None:
        """Verify that listing all submissions works correctly."""
        client, headers, user = setup_user_client(client)

        # this matches how the dummy submissions are created
        for _ in range(3):
            create_submission(original_id=str(uuid4()), completed_by=user)

        assert Submission.objects.count() == 3

        data = {"username": user.username, "count": 2}

        result = client.post(
            reverse("submission-yeet"),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert Submission.objects.count() == 1

    def test_yeet_more_requested_than_available(self, client: Client) -> None:
        """Verify that requesting yeeting more submissions than available is okay."""
        client, headers, user = setup_user_client(client)
        create_submission(original_id=str(uuid4()), completed_by=user)
        assert Submission.objects.count() == 1

        data = {"username": user.username, "count": 10}

        client.post(
            reverse("submission-yeet"),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        assert Submission.objects.count() == 0

    def test_yeet_with_no_count(self, client: Client) -> None:
        """Verify that yeeting without a count only deletes one."""
        client, headers, user = setup_user_client(client)
        for _ in range(4):
            create_submission(original_id=str(uuid4()), completed_by=user)
        assert Submission.objects.count() == 4

        data = {"username": user.username}

        client.post(
            reverse("submission-yeet"),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        assert Submission.objects.count() == 3

    def test_yeet_with_no_user(self, client: Client) -> None:
        """Verify that yeeting without a count only deletes one."""
        client, headers, user = setup_user_client(client)

        response = client.post(
            reverse("submission-yeet"), content_type="application/json", **headers
        )
        assert response.status_code == 400

    def test_yeet_also_removes_linked_transcription(self, client: Client) -> None:
        """Verify that a linked transcription also gets yeeted."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(original_id=str(uuid4()), completed_by=user)
        create_transcription(submission, user)

        assert Submission.objects.count() == 1
        assert Transcription.objects.count() == 1

        data = {"username": user.username}

        client.post(
            reverse("submission-yeet"),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        assert Submission.objects.count() == 0
        assert Transcription.objects.count() == 0
