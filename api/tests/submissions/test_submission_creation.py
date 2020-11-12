import json
from typing import Any
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper
from rest_framework import status

from api.models import Source, Submission, Transcription
from api.tests.helpers import get_default_test_source, setup_user_client


class TestSubmissionCreation:
    """Tests validating the behavior of the Submission creation process."""

    def test_create_minimum_args(self, client: Client) -> None:
        """Test whether creation with minimum arguments is successful."""
        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "content_url": "https://a.com",
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
        assert submission.content_url == data["content_url"]

    def test_submission_create_with_full_args(self, client: Client) -> None:
        """Test whether creation with all arguments is successful."""
        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "url": "http://example.com",
            "tor_url": "http://example.com/tor",
            "content_url": "http://a.com",
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
        assert submission.content_url == data["content_url"]

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
        data = {
            "original_id": "spaaaaace",
            "source": "asdf",
            "content_url": "http://a.com",
        }
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

    def test_ocr_on_create(
        self, client: Client, settings: SettingsWrapper, setup_site: Any
    ) -> None:
        """Verify that a new submission completes the OCR process."""
        settings.ENABLE_OCR = True
        settings.IMAGE_DOMAINS = ["example.com"]
        assert Transcription.objects.count() == 0

        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "content_url": "http://example.com/a.jpg",
        }

        with patch("api.models.process_image", return_value={"text": "AAA"}) as mock:
            result = client.post(
                reverse("submission-list"),
                data,
                content_type="application/json",
                **headers,
            )
            mock.assert_called_once()

        assert result.status_code == status.HTTP_201_CREATED
        assert Transcription.objects.count() == 1
        transcription = Transcription.objects.first()
        assert transcription.text == "AAA"
        assert transcription.source == Source.objects.get(name="blossom")

    def test_failed_ocr_on_create(
        self, client: Client, settings: SettingsWrapper, setup_site: Any
    ) -> None:
        """Verify that a new submission completes the OCR process."""
        settings.ENABLE_OCR = True
        settings.IMAGE_DOMAINS = ["example.com"]
        assert Transcription.objects.count() == 0

        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "content_url": "http://example.com/a.jpg",
        }

        with patch("api.models.process_image", return_value=None) as mock:
            result = client.post(
                reverse("submission-list"),
                data,
                content_type="application/json",
                **headers,
            )
            mock.assert_called_once()

        assert result.status_code == status.HTTP_201_CREATED
        assert Transcription.objects.count() == 0
        assert result.json().get("cannot_ocr") is True
