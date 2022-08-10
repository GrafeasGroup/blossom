import random
from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.shortcuts import reverse
from django.test import Client, RequestFactory
from pytest_django.fixtures import SettingsWrapper
from rest_framework import status

from blossom.api.models import Transcription
from blossom.app.views import TranscribeSubmission
from blossom.utils.test_helpers import (
    add_social_auth_to_user,
    create_submission,
    create_user,
    setup_user_client,
)


def test_accept_coc(client: Client) -> None:
    """Verify that accepting the code of conduct works as expected."""
    client, _, user = setup_user_client(client, accepted_coc=False)
    response = client.get(reverse("accept_coc"))
    assert "Code of Conduct" in response.content.decode()

    assert user.accepted_coc is False

    response = client.post(reverse("accept_coc"))
    assert reverse("choose_transcription") in response.url
    user.refresh_from_db()
    assert user.accepted_coc is True


def test_unclaim_submission(client: Client) -> None:
    """Verify that unclaiming a transcription works as expected."""
    client, _, user = setup_user_client(client)
    add_social_auth_to_user(user)

    submission = create_submission(claimed_by=user)

    response = client.get(
        reverse("app_unclaim", kwargs={"submission_id": submission.id})
    )
    assert reverse("choose_transcription") in response.url


@pytest.mark.parametrize(
    ("error", "expected_redirect"),
    [
        (status.HTTP_423_LOCKED, "logout"),
        (status.HTTP_406_NOT_ACCEPTABLE, "choose_transcription"),
        (status.HTTP_409_CONFLICT, "choose_transcription"),
    ],
)
def test_unclaim_errors(client: Client, error: int, expected_redirect: str) -> None:
    """Verify that errors redirect as they should."""
    client, _, user = setup_user_client(client)
    add_social_auth_to_user(user)

    submission = create_submission(claimed_by=user)

    class Response:
        ...

    response = Response()
    response.status_code = error

    with patch(
        "blossom.api.views.submission.SubmissionViewSet.unclaim",
        lambda a, b, c: response,
    ):
        response = client.get(
            reverse("app_unclaim", kwargs={"submission_id": submission.id})
        )
        assert reverse(expected_redirect) in response.url

    # the unclaim should not have succeeded
    assert submission.claimed_by == user


class TestChooseSubmission:
    def test_choose_transcription(self, client: Client) -> None:
        """Verify that recent submissions are available to choose."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission_1 = create_submission(
            original_id=int(random.random() * 1000),
            title="a",
            content_url="http://imgur.com",
        )
        submission_2 = create_submission(
            original_id=int(random.random() * 1000),
            title="b",
            content_url="http://imgur.com",
        )
        response = client.get(reverse("choose_transcription"))

        assert submission_1 in response.context["options"]
        assert submission_2 in response.context["options"]

    def test_from_multiple_options(self, client: Client) -> None:
        """Verify that with multiple options, we still only get three."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        for _ in range(10):
            create_submission(
                original_id=int(random.random() * 1000),
                title="abc",
                content_url="http://imgur.com",
            )

        response = client.get(reverse("choose_transcription"))

        assert len(response.context["options"]) == 3
        # are they all different?
        assert len(set(response.context["options"])) == 3

    def test_invalid_options(self, client: Client) -> None:
        """Verify that only image posts are returned."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        for _ in range(10):
            create_submission(
                original_id=int(random.random() * 1000),
                title="abc",
                content_url="http://example.com",
            )

        response = client.get(reverse("choose_transcription"))

        assert len(response.context["options"]) == 0
        assert "show_error_page" in response.context

    def test_check_reddit_for_missing_information(
        self, client: Client, settings: SettingsWrapper
    ) -> None:
        """Verify that if information is missing we will check Reddit for it."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)
        settings.ENABLE_REDDIT = True

        class RedditSubmission:
            class Response:
                over_18 = True
                title = "AAA"

            def submission(self, **kwargs: Any) -> Response:
                """Return a mocked response from Reddit."""
                return self.Response()

        with patch(
            "blossom.app.middleware.configure_reddit", lambda a: RedditSubmission()
        ):
            submission = create_submission(
                original_id=int(random.random() * 1000),
                content_url="http://imgur.com",
            )

            client.get(reverse("choose_transcription"))

            submission.refresh_from_db()
            assert submission.title == "AAA"
            assert submission.nsfw is True

    def test_rank_up(self, client: Client) -> None:
        """Verify that confetti gets passed to the page when a user ranks up."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
        )

        with patch("blossom.authentication.models.BlossomUser.ranked_up", True):
            response = client.get(reverse("choose_transcription"))
            assert response.context.get("show_confetti") is True

        with patch("blossom.authentication.models.BlossomUser.ranked_up", False):
            response = client.get(reverse("choose_transcription"))
            assert response.context.get("show_confetti") is None

    def test_no_error_page_with_completed_posts(self, client: Client) -> None:
        """Verify that if completed posts exist, we don't show an error page."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
            completed_by=user,
        )

        response = client.get(reverse("choose_transcription"))
        assert len(response.context["options"]) == 0
        assert "show_error_page" not in response.context

    def test_reported_post_is_removed(self, client: Client) -> None:
        """Verify that a reported post is not brought back to the page."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            title="a",
            content_url="http://imgur.com",
        )

        response = client.get(reverse("choose_transcription"))

        assert submission in response.context["options"]

        # Now we'll report it and verify that it's not rolled anymore
        client.get(reverse("app_report", kwargs={"submission_id": submission.id}))
        response = client.get(reverse("choose_transcription"))
        assert submission not in response.context["options"]


class TestTranscribeSubmission:
    def test_load_page(self, client: Client) -> None:
        """Verify that the transcription page loads as expected."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
        )
        assert submission.claimed_by is None

        response = client.get(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id})
        )

        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.claimed_by == user

    @pytest.mark.parametrize(
        ("error", "expected_redirect"),
        [
            (status.HTTP_423_LOCKED, "logout"),
            (460, "choose_transcription"),
            (status.HTTP_409_CONFLICT, "choose_transcription"),
        ],
    )
    def test_get_errors(
        self, client: Client, error: int, expected_redirect: str
    ) -> None:
        """Verify that errors from the API translate correctly to responses."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
        )

        class Response:
            ...

        response = Response()
        response.status_code = error

        with patch(
            "blossom.api.views.submission.SubmissionViewSet.claim",
            lambda a, b, c: response,
        ):
            response = client.get(
                reverse(
                    "transcribe_submission", kwargs={"submission_id": submission.id}
                )
            )
            assert reverse(expected_redirect) in response.url

    def test_image_proxies(self, client: Client) -> None:
        """Verify that the transcription page loads as expected."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        # Imgur direct link
        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com/aaa.png",
            title="a",
        )

        response = client.get(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id})
        )

        assert "imgur_content_url" in response.context
        assert response.context["imgur_content_url"] == "aaa.png"

        # Imgur post link
        submission.claimed_by = None
        submission.content_url = "http://imgur.com/aaa"
        submission.save()

        response = client.get(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id})
        )
        assert "imgur_content_url" in response.context
        assert response.context["imgur_content_url"] == "aaa.jpg"

        # Reddit link
        submission.claimed_by = None
        submission.content_url = "i.redd.it/bbb"
        submission.save()

        response = client.get(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id})
        )
        assert "ireddit_content_url" in response.context
        assert response.context["ireddit_content_url"] == "bbb"

    def test_session(self, rf: RequestFactory) -> None:
        """Verify that session data is either kept or discarded as appropriate."""
        user = create_user()
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com/aaa",
            title="a",
        )
        request = rf.get(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id}),
        )
        SessionMiddleware().process_request(request)
        request.session.save()

        request.user = user
        request.session["submission_id"] = submission.id
        request.session["heading"] = "AAA"
        request.session["issues"] = ["heading_with_dashes"]
        request.session["transcription"] = "BBB"

        response = TranscribeSubmission().get(request, submission.id)

        assert "AAA" in response.content.decode()
        assert "BBB" in response.content.decode()

        request.session["submission_id"] = 999999

        response = TranscribeSubmission().get(request, submission.id)
        # it should have detected that the content is for a different submission,
        # to the session data should no longer be there
        assert "AAA" not in response.content.decode()
        assert "BBB" not in response.content.decode()

    def test_post(self, client: Client) -> None:
        """Verify that posting a valid transcription completes the process."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com/aaa",
            title="a",
            claimed_by=user,
        )
        assert submission.completed_by is None

        with patch("blossom.api.views.submission.send_check_message"):
            response = client.post(
                reverse(
                    "transcribe_submission", kwargs={"submission_id": submission.id}
                ),
                data={"transcription": "AAA"},
            )

        submission.refresh_from_db()
        assert reverse("choose_transcription") in response.url
        assert submission.completed_by == user
        assert Transcription.objects.count() == 1

    @pytest.mark.parametrize(
        ("error", "expected_redirect"),
        [
            (status.HTTP_423_LOCKED, "logout"),
            (status.HTTP_409_CONFLICT, "choose_transcription"),
        ],
    )
    def test_post_errors(
        self, client: Client, error: int, expected_redirect: str
    ) -> None:
        """Verify that errors from the API translate correctly to responses."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
            claimed_by=user,
        )

        class Response:
            ...

        response = Response()
        response.status_code = error

        with patch(
            "blossom.api.views.submission.SubmissionViewSet.done",
            lambda a, b, c: response,
        ):
            response = client.post(
                reverse(
                    "transcribe_submission", kwargs={"submission_id": submission.id}
                ),
                data={"transcription": "AAA"},
            )
            assert reverse(expected_redirect) in response.url

    def test_post_formatting_errors(self, client: Client) -> None:
        """Verify that correctable formatting issues are handled."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
            claimed_by=user,
        )

        with patch("blossom.api.views.submission.send_check_message"):
            client.post(
                reverse(
                    "transcribe_submission", kwargs={"submission_id": submission.id}
                ),
                data={
                    "transcription": "u/aaa ! Check this out!\n```\nabcde\n```\n\nayy"
                },
            )

        assert "`" not in Transcription.objects.first().text
        assert "\\/" in Transcription.objects.first().text

    def test_post_session(self, client: Client) -> None:
        """Verify that the session gets set appropriately if errors arise."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
            claimed_by=user,
        )

        response = client.post(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id}),
            data={"transcription": "#aaa"},
        )
        assert (
            reverse("transcribe_submission", kwargs={"submission_id": submission.id})
            in response.url
        )
        assert response.wsgi_request.session["transcription"] == "#aaa"
        assert response.wsgi_request.session["submission_id"] == submission.id
        assert response.wsgi_request.session["heading"] is None

    def test_post_no_transcription(self, client: Client) -> None:
        """Verify that submitting without a transcription throws an error."""
        client, _, user = setup_user_client(client)
        add_social_auth_to_user(user)

        submission = create_submission(
            original_id=int(random.random() * 1000),
            content_url="http://imgur.com",
            title="a",
            claimed_by=user,
        )
        response = client.post(
            reverse("transcribe_submission", kwargs={"submission_id": submission.id}),
            data={"transcription": ""},
        )
        assert (
            reverse("transcribe_submission", kwargs={"submission_id": submission.id})
            in response.url
        )
