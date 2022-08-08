import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubmissionNsfw:
    """Tests validating the behavior of marking submissions as NSFW."""

    def test_nsfw_no_params(self, client: Client) -> None:
        """Verify that marking a submission as NSFW works without parameters."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3)
        assert not submission.nsfw

        data = {}

        result = client.patch(
            reverse("submission-nsfw", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_200_OK
        assert submission.nsfw

    def test_nsfw_no_change(self, client: Client) -> None:
        """Verify that setting a submission NSFW twice doesn't change anything."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3, nsfw=True)
        assert submission.nsfw

        data = {}

        result = client.patch(
            reverse("submission-nsfw", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_200_OK
        assert submission.nsfw

    def test_nsfw_param_false(self, client: Client) -> None:
        """Verify that marking a submission as NSFW can be reversed."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3, nsfw=True)
        assert submission.nsfw

        data = {"nsfw": False}

        result = client.patch(
            reverse("submission-nsfw", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_200_OK
        assert not submission.nsfw

    def test_remove_param_true(self, client: Client) -> None:
        """Verify that marking a submission as NSFW works with parameters."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(id=3)
        assert not submission.nsfw

        data = {"nsfw": True}

        result = client.patch(
            reverse("submission-nsfw", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers
        )

        submission.refresh_from_db()

        assert result.status_code == status.HTTP_200_OK
        assert submission.nsfw
