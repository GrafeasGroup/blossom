from typing import Any

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from api.tests.helpers import create_submission, create_transcription, setup_user_client


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
        assert len(result.data) == 1
        create_transcription(submission, transcribot)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # now the submission has a transcribot entry
        assert len(result.data) == 0

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

        assert len(result.data) == 1

        create_transcription(submission, transcribot)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # all submissions have valid OCR transcriptions
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

        assert len(result.data) == 1

        create_transcription(submission, user)

        result = client.get(
            reverse("submission-get-transcribot-queue") + "?source=reddit",
            content_type="application/json",
            **headers,
        )

        # there should be no change to the OCR queue
        assert len(result.data) == 1
