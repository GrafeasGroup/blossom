import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.tests.helpers import create_submission, create_user, setup_user_client


class TestSubmissionClaim:
    """Tests that validate the behavior of the Submission claim process."""

    def test_claim(self, client: Client) -> None:
        """Test whether claim process works correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {"username": user.username}
        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            data,
            content_type="application/json",
            **headers,
        )
        submission.refresh_from_db()
        assert result.status_code == status.HTTP_201_CREATED
        assert result.json()["id"] == submission.id
        assert submission.claimed_by == user

    def test_claim_invalid_original_id(self, client: Client) -> None:
        """Test whether a claim with an invalid submission id is successfully caught."""
        client, headers, user = setup_user_client(client)
        data = {"username": user.username}
        result = client.patch(
            reverse("submission-claim", args=[404]),
            data,
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_claim_invalid_username(self, client: Client) -> None:
        """Test whether a claim with an invalid username is successfully caught."""
        client, headers, _ = setup_user_client(client)
        submission = create_submission()
        data = {"username": "non_existent_username"}
        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_claim_no_user_info(self, client: Client) -> None:
        """Test whether a claim without user information is successfully caught."""
        client, headers, _ = setup_user_client(client)
        submission = create_submission()
        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_claim_already_claimed_same_user(self, client: Client) -> None:
        """Test a claim on a Submission already claimed by the same user.

        This should be prevented and return an error.
        """
        client, headers, user = setup_user_client(client, id=1, username="user_1")
        submission = create_submission(claimed_by=user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_409_CONFLICT
        claimed_by = result.json()
        assert claimed_by["id"] == 1
        assert claimed_by["username"] == "user_1"

        submission.refresh_from_db()
        assert submission.claimed_by == user

    def test_claim_already_claimed_other_user(self, client: Client) -> None:
        """Test a claim on a Submission already claimed by another user.

        This should be prevented and return an error.
        """
        client, headers, user = setup_user_client(client, id=1, username="user_1")
        other_user = create_user(id=2, username="user_2")
        submission = create_submission(claimed_by=other_user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_409_CONFLICT
        claimed_by = result.json()
        assert claimed_by["id"] == 2
        assert claimed_by["username"] == "user_2"

        submission.refresh_from_db()
        assert submission.claimed_by == other_user

    def test_claim_no_coc(self, client: Client) -> None:
        """Test that a claim cannot be completed without accepting the CoC."""
        client, headers, user = setup_user_client(client)
        user.accepted_coc = False
        user.save()

        submission = create_submission()
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_403_FORBIDDEN
        submission.refresh_from_db()
        assert submission.claimed_by is None

    def test_claim_blacklisted_user(self, client: Client) -> None:
        """Test whether claim process errors with a blacklisted user."""
        client, headers, user = setup_user_client(client)
        user.blacklisted = True
        user.save()

        submission = create_submission()
        data = {"username": user.username}
        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            data,
            content_type="application/json",
            **headers,
        )
        submission.refresh_from_db()
        assert result.status_code == status.HTTP_423_LOCKED
        assert submission.claimed_by is None
