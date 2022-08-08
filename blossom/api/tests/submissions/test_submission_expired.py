from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from blossom.api.models import Source
from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubmissionExpired:
    """Tests that validate the behavior of the Submission expired request."""

    def test_expired(self, client: Client) -> None:
        """Test whether only the expired submission is returned."""
        client, headers, _ = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")

        first = create_submission(
            create_time=timezone.now() - timezone.timedelta(days=3), source=reddit
        )
        create_submission(source=reddit)

        result = client.get(
            reverse("submission-expired") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == first.id

    def test_expired_no_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when no submissions are expired."""
        client, headers, _ = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")

        create_submission(source=reddit)

        result = client.get(
            reverse("submission-expired") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_expired_ctq_mode(self, client: Client) -> None:
        """Check whether all posts are returned when CTQ is enabled."""
        client, headers, _ = setup_user_client(client)

        reddit, _ = Source.objects.get_or_create(name="reddit")
        submission = create_submission(source=reddit)

        result = client.get(
            reverse("submission-expired") + "?ctq=1&source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()[0]["id"] == submission.id

    def test_expired_hours_param(self, client: Client) -> None:
        """Check that posts over a certain age can be dynamically returned as expired."""
        client, headers, _ = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")
        # submission #1 -- this is not expired
        create_submission(source=reddit)
        # submission #2 -- not normally expired
        submission2 = create_submission(source=reddit)
        submission2.create_time = timezone.now() - timezone.timedelta(hours=3)
        submission2.save()
        # submission #3 -- very expired
        submission3 = create_submission(source=reddit)
        submission3.create_time = timezone.now() - timezone.timedelta(days=1)
        submission3.save()

        result = client.get(
            reverse("submission-expired") + "?hours=2&source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 2
        for item in result.json():
            assert item["id"] in [submission2.id, submission3.id]

        # Now just ask for regular expired submissions. We should receive one
        # entry back.
        result = client.get(
            reverse("submission-expired") + "?source=reddit",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == submission3.id

    def test_expired_invalid_time(self, client: Client) -> None:
        """Check that requesting an invalid time will return an error."""
        client, headers, _ = setup_user_client(client)
        reddit, _ = Source.objects.get_or_create(name="reddit")

        # this submission should not be returned
        submission1 = create_submission(source=reddit)
        submission1.create_time = timezone.now() - timezone.timedelta(hours=3)
        submission1.save()

        result = client.get(
            reverse("submission-expired") + "?hours=asdf&source=reddit",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_source(self, client: Client) -> None:
        """Verify that requesting unarchived posts without a source errors out."""
        client, headers, user = setup_user_client(client)

        result = client.get(
            reverse("submission-expired"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_source(self, client: Client) -> None:
        """Verify that requesting unarchived posts without a source errors out."""
        client, headers, user = setup_user_client(client)

        result = client.get(
            reverse("submission-expired") + "?source=ABCDEFG",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_404_NOT_FOUND
