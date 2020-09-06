from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.tests.helpers import create_submission, setup_user_client


class TestSubmissionGet:
    """Tests validating the behavior of the Submission retrieval process."""

    def test_list(self, client: Client) -> None:
        """Verify that listing all submissions works correctly."""
        client, headers, _ = setup_user_client(client)
        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 0

        submission = create_submission()

        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 1
        assert result.json()["results"][0]["id"] == submission.id

    def test_get_submissions(self, client: Client) -> None:
        """Test whether all current submissions are provided when no args are provided."""
        client, headers, _ = setup_user_client(client)
        first = create_submission()
        second = create_submission(original_id="second")

        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 2
        assert result.json()["results"][0]["id"] == first.id
        assert result.json()["results"][1]["id"] == second.id

    def test_get_specific_id(self, client: Client) -> None:
        """Test whether the specific submission is provided when an ID is supplied."""
        client, headers, _ = setup_user_client(client)
        first = create_submission()
        create_submission(original_id="second")

        result = client.get(
            reverse("submission-list") + f"?original_id={first.original_id}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert result.json()["results"][0]["id"] == first.id
