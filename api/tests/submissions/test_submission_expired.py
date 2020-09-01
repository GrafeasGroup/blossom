from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.tests.helpers import create_submission, setup_user_client


class TestSubmissionExpired:
    """Tests that validate the behavior of the Submission expired request."""

    def test_expired(self, client: Client) -> None:
        """Test whether only the expired submission is returned."""
        client, headers, _ = setup_user_client(client)
        first = create_submission(
            create_time=timezone.now() - timezone.timedelta(days=3)
        )
        create_submission()

        result = client.get(
            reverse("submission-expired"), content_type="application/json", **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == first.id

    def test_expired_no_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when no submissions are expired."""
        client, headers, _ = setup_user_client(client)

        create_submission()

        result = client.get(
            reverse("submission-expired"), content_type="application/json", **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_expired_ctq_mode(self, client: Client) -> None:
        """Check whether all posts are returned when CTQ is enabled."""
        client, headers, _ = setup_user_client(client)

        submission = create_submission()

        result = client.get(
            reverse("submission-expired") + "?ctq=1",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()[0]["id"] == submission.id

    def test_expired_hours_param(self, client: Client) -> None:
        """Check that posts over a certain age can be dynamically returned as expired."""
        client, headers, _ = setup_user_client(client)

        # submission #1 -- this is not expired
        create_submission()
        # submission #2 -- not normally expired
        submission2 = create_submission()
        submission2.create_time = timezone.now() - timezone.timedelta(hours=3)
        submission2.save()
        # submission #3 -- very expired
        submission3 = create_submission()
        submission3.create_time = timezone.now() - timezone.timedelta(days=1)
        submission3.save()

        result = client.get(
            reverse("submission-expired") + "?hours=2",
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
            reverse("submission-expired"), content_type="application/json", **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == submission3.id

    def test_expired_invalid_time(self, client: Client) -> None:
        """Check that requesting an invalid time will return an error."""
        client, headers, _ = setup_user_client(client)

        # this submission should not be returned
        submission1 = create_submission()
        submission1.create_time = timezone.now() - timezone.timedelta(hours=3)
        submission1.save()

        result = client.get(
            reverse("submission-expired") + "?hours=asdf",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST
