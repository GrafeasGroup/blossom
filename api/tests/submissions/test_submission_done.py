import json
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.tests.helpers import (
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)
from api.views.slack_helpers import client as slack_client


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

    def test_done_no_coc(self, client: Client) -> None:
        """ # noqa
        Test that a submission isn't marked as done when the CoC hasn't been accepted.
        """
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)
        user.accepted_coc = False
        user.save()

        create_transcription(submission, user)
        data = {"username": user.username}

        result = client.patch(
            reverse("submission-done", args=[submission.id]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        submission.refresh_from_db()
        assert result.status_code == status.HTTP_403_FORBIDDEN
        assert submission.claimed_by == user
        assert submission.completed_by is None

    def test_claim_blacklisted_user(self, client: Client) -> None:
        """Test whether claim process errors with blacklisted user."""
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
