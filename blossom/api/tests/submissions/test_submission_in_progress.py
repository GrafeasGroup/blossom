from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from blossom.api.models import Source
from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubmissionsInProgress:
    """Tests that validate the behavior of the Submission unarchived process."""

    def test_in_progress_no_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when there are no submissions."""
        client, headers, _ = setup_user_client(client)
        Source.objects.get_or_create(name="reddit")
        result = client.get(
            reverse("submission-in-progress") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_in_progress_recent_submissions(self, client: Client) -> None:
        """Test that the response is empty when there are no old claimed posts."""
        client, headers, user = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")
        create_submission(
            claimed_by=user,
            claim_time=timezone.now(),
            source=reddit,
        )

        result = client.get(
            reverse("submission-in-progress") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_old_in_progress(self, client: Client) -> None:
        """Test whether an unarchived old post is returned correctly."""
        client, headers, user = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")

        submission = create_submission(
            claimed_by=user,
            claim_time=timezone.now() - timezone.timedelta(hours=5),
            source=reddit,
        )

        result = client.get(
            reverse("submission-in-progress") + "?source=reddit",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == submission.id

    def test_in_progress_custom_time(self, client: Client) -> None:
        """Verify that passing a different time changes the returned submissions."""
        client, headers, user = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")

        submission = create_submission(
            claimed_by=user,
            claim_time=timezone.now() - timezone.timedelta(hours=2),
            source=reddit,
        )

        # will default to four hours, should return nothing
        result = client.get(
            reverse("submission-in-progress") + "?source=reddit",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

        # we'll set a custom hour and now we should get the submission
        result = client.get(
            reverse("submission-in-progress") + "?source=reddit&hours=1",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == submission.id

    def test_missing_source(self, client: Client) -> None:
        """Verify that requesting unarchived posts without a source errors out."""
        client, headers, user = setup_user_client(client)

        result = client.get(
            reverse("submission-in-progress"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_source(self, client: Client) -> None:
        """Verify that requesting unarchived posts without a source errors out."""
        client, headers, user = setup_user_client(client)

        result = client.get(
            reverse("submission-in-progress") + "?source=ABCDEFG",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_404_NOT_FOUND
