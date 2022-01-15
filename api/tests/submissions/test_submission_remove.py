import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from utils.test_helpers import create_submission, setup_user_client


class TestSubmissionRemove:
    """Tests validating the behavior of the Submission removal process."""

    def test_remove_no_params(self, client: Client) -> None:
        """Verify that removing a submission works without parameters."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3)
        assert not submission.removed_from_queue

        data = {}

        result = client.patch(
            reverse("submission-remove", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_201_CREATED
        assert submission.removed_from_queue

    def test_remove_no_change(self, client: Client) -> None:
        """Verify that removing a submission works without parameters."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3, removed_from_queue=True)
        assert submission.removed_from_queue

        data = {}

        result = client.patch(
            reverse("submission-remove", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_201_CREATED
        assert submission.removed_from_queue

    def test_remove_param_false(self, client: Client) -> None:
        """Verify that restoring submissions works correctly."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3, removed_from_queue=True)
        assert submission.removed_from_queue

        data = {"removed_from_queue": False}

        result = client.patch(
            reverse("submission-remove", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_201_CREATED
        assert not submission.removed_from_queue

    def test_remove_param_true(self, client: Client) -> None:
        """Verify that removing a submission works without parameters."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3)
        assert not submission.removed_from_queue

        data = {"removed_from_queue": True}

        result = client.patch(
            reverse("submission-remove", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_201_CREATED
        assert submission.removed_from_queue
