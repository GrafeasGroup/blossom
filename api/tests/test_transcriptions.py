"""Tests to validate the behavior of the Transcription View."""
import json

from django.test import Client
from django_hosts.resolvers import reverse
from rest_framework import status

from api.models import Transcription
from api.tests.helpers import create_submission, create_transcription, setup_user_client


class TestTranscriptionCreation:
    """Tests to validate the behavior of the Transcription creation process."""

    def test_create(self, client: Client) -> None:
        """Test whether the creation functions correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }

        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        transcription = Transcription.objects.get(id=result.json()["id"])
        assert result.status_code == status.HTTP_201_CREATED
        assert transcription.submission == submission
        assert transcription.completion_method == data["completion_method"]
        assert transcription.author == user
        assert transcription.transcription_id == data["t_id"]
        assert transcription.url == data["t_url"]
        assert transcription.text == data["t_text"]

    def test_create_ocr_text(self, client: Client) -> None:
        """Test whether the creation of an OCR transcription works correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        # this data comes from tor_ocr and does not have the t_text key
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "ocr_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        transcription = Transcription.objects.get(id=result.json()["id"])
        assert result.status_code == status.HTTP_201_CREATED
        assert transcription.submission == submission
        assert transcription.text is None
        assert transcription.ocr_text == data["ocr_text"]

    def test_create_no_submission_id(self, client: Client) -> None:
        """Test whether a creation without submission ID is caught correctly."""
        client, headers, user = setup_user_client(client)
        data = {
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invalid_submission_id(self, client: Client) -> None:
        """Test whether a creation with an invalid submission ID is caught correctly."""
        client, headers, user = setup_user_client(client)
        data = {
            "submission_id": 404,
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_create_invalid_user_id(self, client: Client) -> None:
        """Test whether a creation with an invalid user ID is caught correctly."""
        client, headers, _ = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": 404,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_create_no_transcription_id(self, client: Client) -> None:
        """Test whether a creation without a Transcription ID is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_completion_method(self, client: Client) -> None:
        """Test whether a creation without a completion method is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "t_id": "ABC",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_transcription_url(self, client: Client) -> None:
        """Test whether a creation without a transcription URL is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_transcription_text(self, client: Client) -> None:
        """Test whether a creation without a transcription text is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_both_text_fields(self, client: Client) -> None:
        """Test whether a creation with both transcription and OCR text is caught."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.submission_id,
            "v_id": user.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
            "ocr_text": "ocr content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST


class TestTranscriptionSearch:
    """Tests validating the Transcription search procedure."""

    def test_search(self, client: Client) -> None:
        """Test whether only transcriptions of the provided Submission are returned."""
        client, headers, user = setup_user_client(client)
        first_sub = create_submission()
        second_sub = create_submission(submission_id="second_submission")
        transcription = create_transcription(first_sub, user)
        create_transcription(second_sub, user)
        result = client.get(
            reverse("transcription-search", host="api")
            + f"?submission_id={first_sub.submission_id}",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == transcription.id

    def test_search_nonexistent_id(self, client: Client) -> None:
        """Test whether no items are returned when a search on a nonexistent ID done."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("transcription-search", host="api") + "?submission_id=404",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert not result.json()

    def test_search_no_submission_id(self, client: Client) -> None:
        """Check whether a search without ID is caught correctly."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("transcription-search", host="api"),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST


class TestTranscriptionRandom:
    """Tests that validate the behavior of the Random Review process."""

    def test_random_none_available(self, client: Client) -> None:
        """Test that no transcription is returned when there is none available."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("transcription-review-random", host="api"),
            HTTP_HOST="api",
            **headers,
        )

        assert not result.content
        assert result.status_code == status.HTTP_200_OK

    def test_random(self, client: Client) -> None:
        """Test whether a transcription is returned when available."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        transcription = create_transcription(submission, user)

        result = client.get(
            reverse("transcription-review-random", host="api"),
            HTTP_HOST="api",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()
        assert result.json()["transcription_id"] == transcription.transcription_id
