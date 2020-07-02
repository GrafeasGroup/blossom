"""Tests to validate the behavior of the Submission View."""
import json
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.models import Submission
from api.tests.helpers import (
    create_submission,
    create_transcription,
    create_user,
    get_default_test_source,
    setup_user_client,
)
from api.views.slack_helpers import client as slack_client


class TestSubmissionCreation:
    """Tests validating the behavior of the Submission creation process."""

    def test_create_minimum_args(self, client: Client) -> None:
        """Test whether creation with minimum arguments is successful."""
        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {"original_id": "spaaaaace", "source": source.pk}
        result = client.post(
            reverse("submission-list"),
            data,
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_201_CREATED
        submission = Submission.objects.get(id=result.json()["id"])
        assert submission.original_id == data["original_id"]
        assert submission.source == source

    def test_submission_create_with_full_args(self, client: Client) -> None:
        """Test whether creation with all arguments is successful."""
        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "url": "http://example.com",
            "tor_url": "http://example.com/tor",
        }
        result = client.post(
            reverse("submission-list"),
            data,
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_201_CREATED
        submission = Submission.objects.get(id=result.json()["id"])
        assert submission.original_id == data["original_id"]
        assert submission.source == source
        assert submission.url == data["url"]
        assert submission.tor_url == data["tor_url"]

    def test_create_no_source(self, client: Client) -> None:
        """Test whether a request without source is considered a bad request."""
        client, headers, _ = setup_user_client(client)
        data = {"original_id": "spaaaaace"}
        result = client.post(
            reverse("submission-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_invalid_source(self, client: Client) -> None:
        """Test whether a request with an invalid source returns a 404."""
        client, headers, _ = setup_user_client(client)
        data = {"original_id": "spaaaaace", "source": "asdf"}
        result = client.post(
            reverse("submission-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_create_no_id(self, client: Client) -> None:
        """Test whether a request without submission ID is considered a bad request."""
        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {"source": source.pk}

        result = client.post(
            reverse("submission-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST


class TestSubmissionGet:
    """Tests validating the behavior of the Submission retrieval process."""

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


class TestSubmissionsUnarchived:
    """Tests that validate the behavior of the Submission unarchived process."""

    def test_unarchived_no_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when there are no submissions."""
        client, headers, _ = setup_user_client(client)

        result = client.get(
            reverse("submission-unarchived"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_unarchived_recent_submissions(self, client: Client) -> None:
        """Test whether an empty list is returned when there are recent submissions."""
        client, headers, user = setup_user_client(client)
        create_submission(
            completed_by=user, complete_time=timezone.now(), archived=False
        )

        result = client.get(
            reverse("submission-unarchived"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 0

    def test_unarchived_old_unarchived(self, client: Client) -> None:
        """Test whether an unarchived old post is returned correctly."""
        client, headers, user = setup_user_client(client)

        submission = create_submission(
            completed_by=user,
            complete_time=timezone.now() - timezone.timedelta(hours=1),
            archived=False,
        )

        result = client.get(
            reverse("submission-unarchived"),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == submission.id


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

    def test_claim_already_claimed(self, client: Client) -> None:
        """Test whether a claim on a Submission already claimed is successfully caught."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-claim", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_409_CONFLICT


class TestSubmissionDone:
    """Tests to validate the behavior of the Submission done process."""

    def test_done(self, client: Client) -> None:
        """Test whether done process works correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)
        create_transcription(submission, user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_201_CREATED
        assert submission.claimed_by == user
        assert submission.completed_by == user
        assert result.json()["original_id"] == submission.original_id

    def test_done_without_transcription(self, client: Client) -> None:
        """Test that the `done` endpoint errors out appropriately if data is missing."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_428_PRECONDITION_REQUIRED
        assert submission.claimed_by == user
        assert submission.completed_by is None

    def test_done_without_claim(self, client: Client) -> None:
        """Test whether a done without the submission claimed is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_412_PRECONDITION_FAILED

    def test_done_different_claim(self, client: Client) -> None:
        """Test whether a done with a claim from another user is caught correctly."""
        client, headers, user = setup_user_client(client)
        claiming_user = create_user(username="claiming_user")
        submission = create_submission(claimed_by=claiming_user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_412_PRECONDITION_FAILED

    def test_done_without_user_info(self, client: Client) -> None:
        """Test whether a done without user information is caught correctly."""
        client, headers, _ = setup_user_client(client)
        submission = create_submission()

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_done_already_completed(self, client: Client) -> None:
        """Test whether a done on an already completed submission is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user, completed_by=user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "probability,gamma,message,tor_url,trans_url",
        [
            (0.8, 0, False, None, None),
            (0.7999, 50, True, None, None),
            (0.7, 51, False, None, None),
            (0.6999, 100, True, None, None),
            (0.6, 101, False, None, None),
            (0.5999, 250, True, None, None),
            (0.5, 251, False, None, None),
            (0.4999, 500, True, None, None),
            (0.3, 501, False, None, None),
            (0.2999, 1000, True, None, None),
            (0.1, 1001, False, None, None),
            (0.0999, 5000, True, None, None),
            (0.05, 5001, False, None, None),
            (0.0499, 10000, True, None, None),
            (0, 0, True, "url", None),
            (0, 0, True, "tor_url", "trans_url"),
        ],
    )
    def test_done_random_checks(
        self,
        client: Client,
        probability: float,
        gamma: int,
        message: bool,
        tor_url: [str, None],
        trans_url: [str, None],
    ) -> None:
        """Test whether the random checks for the done process are invoked correctly."""
        # Mock both the gamma property and the random.random function.
        with patch(
            "authentication.models.BlossomUser.gamma", new_callable=PropertyMock
        ) as mock, patch("random.random", lambda: probability):
            mock.return_value = gamma
            # Mock the Slack client to catch the sent messages by the function under test.
            slack_client.chat_postMessage = MagicMock()

            client, headers, user = setup_user_client(client)
            submission = create_submission(tor_url=tor_url, claimed_by=user)
            create_transcription(submission, user, url=trans_url)

            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )
            slack_message = (
                f"Please check the following transcription of u/{user.username}: "
                f"{trans_url if trans_url else tor_url}."
            )
            assert result.status_code == status.HTTP_201_CREATED
            if message:
                assert (
                    call(channel="#transcription_check", text=slack_message)
                    == slack_client.chat_postMessage.call_args_list[-1]
                )
            else:
                assert slack_client.chat_postMessage.call_count == 0


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
        assert submission.claim_time is None

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
