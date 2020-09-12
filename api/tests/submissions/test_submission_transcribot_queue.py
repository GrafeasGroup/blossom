from typing import Any
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from api.tests.helpers import create_submission, create_transcription, setup_user_client
from api.views.submission import SubmissionViewSet


class TestSubmissionTranscribotQueue:
    def test_get_transcribot_queue(self, client: Client, setup_site: Any) -> None:
        """Test that the OCR queue endpoint returns the correct data."""
        client, headers, _ = setup_user_client(client)
        user_model = get_user_model()
        transcribot = user_model.objects.get(username="transcribot")

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert len(result.data) == 0  # there are no posts to work on

        submission = create_submission(source="reddit")

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # now there's a submission without a transcribot transcription
        assert len(result.data) == 0
        create_transcription(submission, transcribot, original_id=None)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # now the submission has a transcribot entry
        assert len(result.data) == 1

    def test_completed_ocr_transcriptions(
        self, client: Client, setup_site: Any
    ) -> None:
        """Test that a completed transcription removes the submission from the queue."""
        client, headers, _ = setup_user_client(client)
        user_model = get_user_model()
        transcribot = user_model.objects.get(username="transcribot")
        submission = create_submission(source="reddit")

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert len(result.data) == 0

        transcription = create_transcription(submission, transcribot, original_id=None)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # now there's a transcription that needs work
        assert len(result.data) == 1

        # transcribot works on it
        transcription.original_id = "AAA"
        transcription.save()

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # Queue goes back to 0.
        assert len(result.data) == 0

    def test_normal_transcriptions_dont_affect_ocr_queue(
        self, client: Client, setup_site: Any
    ) -> None:
        """Verify that a human-completed transcription doesn't affect the OCR queue."""
        client, headers, user = setup_user_client(client)
        submission = create_submission(source="reddit")

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        assert len(result.data) == 0

        create_transcription(submission, user)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # there should be no change to the OCR queue
        assert len(result.data) == 0

    def test_transcribot_limit_param(self, client: Client, setup_site: Any) -> None:
        """Verify that adding the `limit` QSP modifies the results."""
        client, headers, _ = setup_user_client(client)
        user_model = get_user_model()
        transcribot = user_model.objects.get(username="transcribot")

        submission1 = create_submission(source="reddit", original_id="A")
        submission2 = create_submission(source="reddit", original_id="B")
        submission3 = create_submission(source="reddit", original_id="C")

        create_transcription(submission1, transcribot, original_id=None)
        create_transcription(submission2, transcribot, original_id=None)
        create_transcription(submission3, transcribot, original_id=None)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit&limit=none",
            content_type="application/json",
            **headers,
        )

        assert len(result.data) == 3

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit&limit=1",
            content_type="application/json",
            **headers,
        )

        assert len(result.data) == 1
        assert result.json()[0]["id"] == submission1.id


def test_get_limit() -> None:
    """Verify that get_limit_value returns the requested value or 10."""
    request = MagicMock()
    request.query_params.get.return_value = None
    return_value = SubmissionViewSet()._get_limit_value(request)
    assert return_value == 10

    request.query_params.get.return_value = None
    return_value = SubmissionViewSet()._get_limit_value(request, default=200)
    assert return_value == 200

    request.query_params.get.return_value = "999"
    return_value = SubmissionViewSet()._get_limit_value(request)
    assert return_value == 999

    request.query_params.get.return_value = "none"
    return_value = SubmissionViewSet()._get_limit_value(request)
    assert return_value is None

    request.query_params.get.return_value = "aaa"
    return_value = SubmissionViewSet()._get_limit_value(request)
    assert return_value == 10

    request.query_params.get.return_value = "!@#$%&%)%^&"
    return_value = SubmissionViewSet()._get_limit_value(request)
    assert return_value == 10
