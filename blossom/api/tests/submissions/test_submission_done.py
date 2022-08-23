import json
from unittest.mock import PropertyMock, patch

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)


class TestSubmissionDone:
    """Tests to validate the behavior of the Submission done process."""

    def test_done(self, client: Client) -> None:
        """Test whether done process works correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)
        create_transcription(submission, user)
        data = {"username": user.username}

        with patch("blossom.api.views.submission.send_check_message"):
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

    def test_done_without_transcription_with_override(self, client: Client) -> None:
        """Test calling `done` with mod override ignores the need for transcription."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(claimed_by=user)
        data = {"username": user.username, "mod_override": "True"}
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
        "should_check_transcription",
        [True, False],
    )
    def test_done_random_checks(
        self,
        client: Client,
        should_check_transcription: bool,
    ) -> None:
        """Test whether the random checks for the done process are invoked correctly."""
        with patch(
            "blossom.authentication.models.BlossomUser.should_check_transcription",
            return_value=should_check_transcription,
        ), patch("blossom.api.views.submission.send_check_message") as mock:
            client, headers, user = setup_user_client(client)
            submission = create_submission(url="abc", tor_url="def", claimed_by=user)
            create_transcription(submission, user, url="ghi")

            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )
            assert result.status_code == status.HTTP_201_CREATED
            if should_check_transcription:
                assert mock.call_count == 1
            else:
                assert mock.call_count == 0

    @pytest.mark.parametrize(
        "gamma, expected",
        [(24, False), (25, True), (26, False)],
    )
    def test_check_for_rank_up(
        self, client: Client, gamma: int, expected: bool
    ) -> None:
        """Verify that a slack message fires when a volunteer ranks up."""
        client, headers, user = setup_user_client(client)
        for iteration in range(24):
            create_submission(claimed_by=user, completed_by=user)

        submission = create_submission(claimed_by=user, original_id=25)

        # patch out transcription check
        with patch(
            "blossom.authentication.models.BlossomUser.should_check_transcription",
            return_value=False,
        ), patch(
            "blossom.authentication.models.BlossomUser.gamma",
            new_callable=PropertyMock,
            return_value=gamma,
        ), patch(
            "blossom.api.slack.client.chat_postMessage"
        ) as mock:
            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username, "mod_override": "True"}),
                content_type="application/json",
                **headers,
            )
            assert result.status_code == status.HTTP_201_CREATED

            if expected:
                assert mock.call_count == 1
                slack_message = (
                    f"Congrats to {user.username} on "
                    f"achieving the rank of {user.get_rank()}!!"
                    f" {submission.tor_url}"
                )
                assert mock.call_args[1]["text"] == slack_message
            else:
                assert mock.call_count == 0

    def test_done_no_coc(self, client: Client) -> None:
        """# noqa
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

    def test_claim_blocked_user(self, client: Client) -> None:
        """Test whether claim process errors with blocked user."""
        client, headers, user = setup_user_client(client)
        user.blocked = True
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
