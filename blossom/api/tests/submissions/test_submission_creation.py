import json
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper
from rest_framework import status

from blossom.api.models import Source, Submission, Transcription
from blossom.utils.test_helpers import get_default_test_source, setup_user_client


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
            "title": "This is a Submission",
            "nsfw": False,
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
        assert submission.nsfw == data["nsfw"]
        assert submission.title == data["title"]

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

    @pytest.mark.parametrize(
        "test_input,output",
        [
            ("AAA", "AAA"),
            ("hi, u/ToR!", "hi, \/u/ToR!"),  # noqa: W605
            ("https://aaa.com/aaaa", "<redacted link>"),
            ("https://aaa.com/", "https://aaa.com/"),
            (
                "https://aaa.com/aaaa -- it's the best, u/aa!",
                "<redacted link> -- it's the best, \/u/aa!",  # noqa: W605
            ),
        ],
    )
    def test_ocr_on_create(
        self,
        client: Client,
        settings: SettingsWrapper,
        test_input: str,
        output: str,
    ) -> None:
        """Verify that a new submission completes the OCR process."""
        settings.ENABLE_OCR = True
        settings.IMAGE_DOMAINS = ["example.com"]
        assert Transcription.objects.count() == 0

        client, headers, _ = setup_user_client(client)
        source = get_default_test_source("reddit")
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "content_url": "http://example.com/a.jpg",
        }

        with patch(
            "blossom.api.models.process_image", return_value={"text": test_input}
        ) as mock:
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
        assert transcription.text == output
        assert transcription.source == Source.objects.get(name="blossom")

    def test_ocr_on_create_with_cannot_ocr_flag(
        self, client: Client, settings: SettingsWrapper
    ) -> None:
        """Verify the OCR process exits early if the cannot_ocr flag is already set."""
        settings.ENABLE_OCR = True
        settings.IMAGE_DOMAINS = ["example.com"]
        assert Transcription.objects.count() == 0

        client, headers, _ = setup_user_client(client)
        source = get_default_test_source()
        data = {
            "original_id": "spaaaaace",
            "source": source.pk,
            "content_url": "http://example.com/a.jpg",
            "cannot_ocr": "True",
        }

        with patch(
            "blossom.api.models.process_image", return_value={"text": "AAA"}
        ) as mock:
            # mock it anyway just in case this fails -- we don't want to actually
            # call OCR
            result = client.post(
                reverse("submission-list"),
                data,
                content_type="application/json",
                **headers,
            )
            mock.assert_not_called()

        assert result.status_code == status.HTTP_201_CREATED
        assert Transcription.objects.count() == 0

    def test_failed_ocr_on_create(
        self, client: Client, settings: SettingsWrapper
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

        with patch("blossom.api.models.process_image", return_value=None) as mock:
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
