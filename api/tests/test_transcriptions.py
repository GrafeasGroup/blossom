"""Tests to validate the behavior of the Transcription View."""
import json

from django.test import Client
from django_hosts.resolvers import reverse
from rest_framework import status

from api.models import Transcription
from api.tests.helpers import (
    create_submission, create_transcription, setup_user_client, get_default_test_source
)


class TestTranscriptionCreation:
    """Tests to validate the behavior of the Transcription creation process."""

    def test_create(self, client: Client) -> None:
        """Test whether the creation functions correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.original_id,
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
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
        assert transcription.source == submission.source
        assert transcription.author == user
        assert transcription.original_id == data["original_id"]
        assert transcription.url == data["t_url"]
        assert transcription.text == data["t_text"]

    def test_create_no_submission_id(self, client: Client) -> None:
        """
        Test whether a creation without passing `submission_id` is caught correctly.
        """
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
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
        source = get_default_test_source()
        data = {
            "submission_id": 404,
            "v_id": user.id,
            "t_id": "ABC",
            "source": source.name,
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
            "submission_id": submission.original_id,
            "v_id": 404,
            "t_id": "ABC",
            "source": submission.source.name,
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
            "original_id": submission.original_id,
            "v_id": user.id,
            "source": submission.source.name,
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

    def test_create_no_source(self, client: Client) -> None:
        """Test whether a creation without a source is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "original_id": submission.original_id,
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
            "original_id": submission.original_id,
            "v_id": user.id,
            "t_id": "ABC",
            "source": submission.source.name,
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
            "original_id": submission.original_id,
            "v_id": user.id,
            "t_id": "ABC",
            "source": submission.source.name,
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


class TestTranscriptionSearch:
    """Tests validating the Transcription search procedure."""

    def test_search(self, client: Client) -> None:
        """Test whether only transcriptions of the provided Submission are returned."""
        client, headers, user = setup_user_client(client)
        first_sub = create_submission()
        second_sub = create_submission(original_id="second_submission")
        transcription = create_transcription(first_sub, user)
        create_transcription(second_sub, user)
        result = client.get(
            reverse("transcription-search", host="api")
            + f"?original_id={first_sub.original_id}",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == transcription.id

    def test_search_nonexistent_id(self, client: Client) -> None:
        """
        Test whether no items are returned when a search on a nonexistent ID is done.
        """
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("transcription-search", host="api") + "?original_id=404",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert not result.json()

    def test_search_no_original_id(self, client: Client) -> None:
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
        assert result.json()["original_id"] == transcription.original_id
