import datetime
import json
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest
import pytz
from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper
from rest_framework import status

from api.slack import client as slack_client
from api.views.submission import _is_returning_transcriber
from utils.test_helpers import (
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
        "probability,gamma,message,tor_url,trans_url",
        [
            (1, 3, False, None, None),
            (0.8, 10, False, None, None),
            (0.3999, 50, True, None, None),
            (0.7, 51, False, None, None),
            (0.1999, 100, True, None, None),
            (0.6, 101, False, None, None),
            (0.0999, 250, True, None, None),
            (0.5, 251, False, None, None),
            (0.0499, 500, True, None, None),
            (0.3, 501, False, None, None),
            (0.0199, 1000, True, None, None),
            (0.1, 1001, False, None, None),
            (0.0099, 5000, True, None, None),
            (0.05, 5001, False, None, None),
            (0.00499, 10000, True, None, None),
            (0, 1, True, "url", None),
            (0, 1, True, "tor_url", "trans_url"),
        ],
    )
    def test_done_random_checks(
        self,
        client: Client,
        settings: SettingsWrapper,
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
        ) as mock, patch(
            "api.views.submission._is_returning_transcriber", return_value=False
        ), patch(
            "random.random", lambda: probability
        ):
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
                    call(
                        channel=settings.SLACK_TRANSCRIPTION_CHECK_CHANNEL,
                        text=slack_message,
                    )
                    in slack_client.chat_postMessage.call_args_list
                )
            else:
                assert slack_client.chat_postMessage.call_count == 0

    @pytest.mark.parametrize(
        "recent_gamma, total_gamma, expected",
        [(0, 10000, True), (5, 10000, True), (6, 6, False), (10, 10000, False)],
    )
    def test_is_returning_transcriber(
        self, client: Client, recent_gamma: int, total_gamma: int, expected: bool,
    ) -> None:
        """Test whether returning transcribers are determined correctly."""
        # Mock both the total gamma
        with patch(
            "authentication.models.BlossomUser.gamma",
            new_callable=PropertyMock,
            return_value=total_gamma,
        ):
            # Mock the Slack client to catch the sent messages by the function under test.
            client, headers, user = setup_user_client(client)
            now = datetime.datetime.now(tz=pytz.UTC)

            # Create the recent transcriptions
            for i in range(0, recent_gamma):
                submission = create_submission(
                    id=i + 100, claimed_by=user, completed_by=user, complete_time=now,
                )
                create_transcription(submission, user, id=i + 100, create_time=now)

            assert _is_returning_transcriber(user) == expected

    def test_send_transcription_to_slack(
        self, client: Client, settings: SettingsWrapper
    ) -> None:
        """Verify that a new user gets a different welcome message."""
        # Mock both the gamma property and the random.random function.
        with patch(
            "authentication.models.BlossomUser.gamma", new_callable=PropertyMock
        ) as mock:
            mock.return_value = 0
            # Mock the Slack client to catch the sent messages by the function under test.
            slack_client.chat_postMessage = MagicMock()

            client, headers, user = setup_user_client(client)
            submission = create_submission(tor_url="asdf", claimed_by=user)
            create_transcription(submission, user, url=None)

            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )

            first_slack_message = (
                f":rotating_light: First transcription! :rotating_light:"
                f" Please check the following transcription of u/{user.username}:"
                f" asdf."
            )
            second_slack_message = (
                f"Please check the following transcription of u/{user.username}:"
                f" asdf."
            )
            check_slack_message = (
                f"Please check the following transcription of u/{user.username}:"
                f" asdf.\n\nThis user is being watched with a chance of 100%.\n"
                f"Undo this using the `unwatch {user.username}` command."
            )

            assert result.status_code == status.HTTP_201_CREATED
            assert (
                call(
                    channel=settings.SLACK_TRANSCRIPTION_CHECK_CHANNEL,
                    text=first_slack_message,
                )
                == slack_client.chat_postMessage.call_args_list[0]
            )
            submission.refresh_from_db()
            submission.completed_by = None
            submission.save()

            mock.return_value = 1

            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )
            assert result.status_code == status.HTTP_201_CREATED
            assert (
                call(
                    channel=settings.SLACK_TRANSCRIPTION_CHECK_CHANNEL,
                    text=second_slack_message,
                )
                == slack_client.chat_postMessage.call_args_list[-1]
            )
            submission.refresh_from_db()
            submission.completed_by = None
            submission.save()

            user.overwrite_check_percentage = 1
            user.save()
            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )
            assert result.status_code == status.HTTP_201_CREATED
            assert (
                call(
                    channel=settings.SLACK_TRANSCRIPTION_CHECK_CHANNEL,
                    text=check_slack_message,
                )
                == slack_client.chat_postMessage.call_args_list[-1]
            )

    def test_removed_transcription_changes(self, client: Client) -> None:
        """Verify that a removed transcription is not sent to Slack."""
        # Mock both the gamma property and the random.random function.
        with patch(
            "authentication.models.BlossomUser.gamma", new_callable=PropertyMock
        ) as mock:
            mock.return_value = 0
            # Mock the Slack client to catch the sent messages by the function under test.
            slack_client.chat_postMessage = MagicMock()

            client, headers, user = setup_user_client(client)
            submission = create_submission(tor_url="asdf", claimed_by=user)
            create_transcription(submission, user, url=None, removed_from_reddit=True)

            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )

            assert result.status_code == status.HTTP_201_CREATED
            assert len(slack_client.chat_postMessage.call_args_list) == 1

            # A new transcriber with a removed post should get sent. An existing one
            # shouldn't get forwarded since they should hopefully already know what
            # they're doing and we'll see one of their next (not removed) posts anyway.
            mock.return_value = 10
            # reset the slack_client mock
            slack_client.chat_postMessage = MagicMock()
            # reset the submission
            submission.completed_by = None
            submission.complete_time = None
            submission.save()

            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )

            assert result.status_code == status.HTTP_201_CREATED
            assert len(slack_client.chat_postMessage.call_args_list) == 0

    def test_check_for_rank_up(self, client: Client, settings: SettingsWrapper) -> None:
        """Verify that a slack message fires when a volunteer ranks up."""
        client, headers, user = setup_user_client(client)
        for iteration in range(24):
            create_submission(claimed_by=user, completed_by=user)

        # Mock the Slack client to catch the sent messages by the function under test.
        slack_client.chat_postMessage = MagicMock()

        submission = create_submission(claimed_by=user, original_id=25)

        # patch out transcription check
        with patch(
            "api.views.submission._should_check_transcription", return_value=False,
        ):
            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username, "mod_override": "True"}),
                content_type="application/json",
                **headers,
            )
        assert result.status_code == status.HTTP_201_CREATED
        slack_message = (
            f"Congrats to {user.username} on achieving the rank of {user.get_rank()}!!"
            f" {submission.tor_url}"
        )
        assert (
            call(channel=settings.SLACK_RANK_UP_CHANNEL, text=slack_message)
            == slack_client.chat_postMessage.call_args_list[0]
        )

        # now they do another transcription!
        submission = create_submission(claimed_by=user, original_id=26)
        create_transcription(submission, user)

        # now it shouldn't trigger on the next transcription
        # patch out transcription check
        old_count_of_slack_calls = len(slack_client.chat_postMessage.call_args_list)

        with patch(
            "api.views.submission._should_check_transcription", return_value=False,
        ):
            result = client.patch(
                reverse("submission-done", args=[submission.id]),
                json.dumps({"username": user.username}),
                content_type="application/json",
                **headers,
            )
            assert result.status_code == status.HTTP_201_CREATED

        # nothing fired, right?
        assert (
            len(slack_client.chat_postMessage.call_args_list)
            == old_count_of_slack_calls
        )

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
