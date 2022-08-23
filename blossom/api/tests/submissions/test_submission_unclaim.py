import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.utils.test_helpers import create_submission, create_user, setup_user_client


class TestSubmissionUnclaim:
    """Tests that validate the behavior of the Submission unclaim process."""

    def test_unclaim(self, client: Client) -> None:
        """Test whether the unclaim process works correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)

        result = client.patch(
            reverse("submission-unclaim", args=[submission.id]),
            {"username": user.username},
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_201_CREATED
        assert submission.claimed_by is None

    def test_unclaim_unclaimed_submission(self, client: Client) -> None:
        """Test whether unclaiming an unclaimed submission is caught successfully."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()

        result = client.patch(
            reverse("submission-unclaim", args=[submission.id]),
            {"username": user.username},
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_412_PRECONDITION_FAILED

    def test_unclaim_no_username(self, client: Client) -> None:
        """Test whether unclaiming without an username is caught correctly."""
        client, headers, _ = setup_user_client(client)
        submission = create_submission()

        result = client.patch(
            reverse("submission-unclaim", args=[submission.id]),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_unclaim_completed_post(self, client: Client) -> None:
        """Test whether unclaiming a completed post is caught successfully."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user, completed_by=user)

        result = client.patch(
            reverse("submission-unclaim", args=[submission.id]),
            json.dumps({"username": user.username}),
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_409_CONFLICT
        # verify we didn't modify the data
        assert submission.claimed_by == user
        assert submission.completed_by == user

    def test_unclaim_different_user(self, client: Client) -> None:
        """Test whether an unclaim of a submission claimed by another user is caught."""
        client, headers, user = setup_user_client(client)
        claiming_user = create_user(username="claiming_user")
        submission = create_submission(claimed_by=claiming_user)

        result = client.patch(
            reverse("submission-unclaim", args=[submission.id]),
            json.dumps({"username": user.username}),
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_406_NOT_ACCEPTABLE
        assert submission.claimed_by == claiming_user

    def test_unclaim_blocked_user(self, client: Client) -> None:
        """Test whether the unclaim process works correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        user.blocked = True
        user.save()

        submission = create_submission(claimed_by=user)

        result = client.patch(
            reverse("submission-unclaim", args=[submission.id]),
            {"username": user.username},
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_423_LOCKED
        assert submission.claimed_by == user
