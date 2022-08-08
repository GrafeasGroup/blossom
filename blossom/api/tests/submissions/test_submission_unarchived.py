from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from blossom.api.models import Source
from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubmissionsUnarchived:
    """Tests that validate the behavior of the Submission unarchived process."""

    def test_unarchived_no_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when there are no submissions."""
        client, headers, _ = setup_user_client(client)
        Source.objects.get_or_create(name="reddit")
        result = client.get(
            reverse("submission-unarchived") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_unarchived_recent_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when there are recent submissions."""
        client, headers, user = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")
        create_submission(
            completed_by=user,
            complete_time=timezone.now(),
            archived=False,
            source=reddit,
        )

        result = client.get(
            reverse("submission-unarchived") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_unarchived_old_unarchived(self, client: Client) -> None:
        """Test whether an unarchived old post is returned correctly."""
        client, headers, user = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")

        submission = create_submission(
            completed_by=user,
            complete_time=timezone.now() - timezone.timedelta(hours=1),
            archived=False,
            source=reddit,
        )

        result = client.get(
            reverse("submission-unarchived") + "?source=reddit",
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
            reverse("submission-unarchived"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_source(self, client: Client) -> None:
        """Verify that requesting unarchived posts without a source errors out."""
        client, headers, user = setup_user_client(client)

        result = client.get(
            reverse("submission-unarchived") + "?source=ABCDEFG",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_404_NOT_FOUND
