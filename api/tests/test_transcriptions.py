"""Tests to validate the behavior of the Transcription View."""
import json
from datetime import datetime
from typing import List

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status

from api.models import Source, Transcription
from api.tests.helpers import (
    create_submission,
    create_transcription,
    get_default_test_source,
    setup_user_client,
)


class TestTranscriptionCreation:
    """Tests to validate the behavior of the Transcription creation process."""

    def test_list(self, client: Client) -> None:
        """Test that the primary API page for transcriptions works correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()

        result = client.get(
            reverse("transcription-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 0

        create_transcription(submission, user)

        result = client.get(
            reverse("transcription-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 1
        assert result.json()["results"][0]["id"] == 1

    def test_list_with_filters(self, client: Client) -> None:
        """Verify that listing all submissions works correctly."""
        client, headers, user = setup_user_client(client)

        aaa, _ = Source.objects.get_or_create(name="AAA")
        bbb, _ = Source.objects.get_or_create(name="BBB")

        submission = create_submission()

        create_transcription(submission, user, source=aaa)
        create_transcription(submission, user, source=aaa)
        create_transcription(submission, user, source=bbb)
        create_transcription(submission, user, source=bbb)

        result = client.get(
            reverse("transcription-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 4

        result = client.get(
            reverse("transcription-list") + "?source=AAA",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 2
        assert "AAA" in result.json()["results"][0]["source"]  # it will be a full link

        result = client.get(
            reverse("transcription-list") + "?source=AAA&id=1",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert "AAA" in result.json()["results"][0]["source"]  # it will be a full link
        assert result.json()["results"][0]["id"] == 1

    def test_create(self, client: Client) -> None:
        """Test whether the creation functions correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
            "url": "https://example.com",
            "text": "test content",
        }

        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_201_CREATED
        transcription = Transcription.objects.get(id=result.json()["id"])
        assert transcription.submission == submission
        assert transcription.source == submission.source
        assert transcription.author == user
        assert transcription.original_id == data["original_id"]
        assert transcription.url == data["url"]
        assert transcription.text == data["text"]

    def test_create_no_coc(self, client: Client) -> None:
        """Test that no transcription can be created without accepting the CoC."""
        client, headers, user = setup_user_client(client)
        user.accepted_coc = False
        user.save()

        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
            "url": "https://example.com",
            "text": "test content",
        }

        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_403_FORBIDDEN
        assert Transcription.objects.count() == 0

    def test_create_no_submission_id(self, client: Client) -> None:
        """Test whether a creation without passing `submission_id` is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
            "url": "https://example.com",
            "text": "test content",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
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
            "original_id": "base_id",
            "username": user.username,
            "source": source.name,
            "url": "https://example.com",
            "text": "test content",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_create_invalid_username(self, client: Client) -> None:
        """Test whether a creation with an invalid username is caught correctly."""
        client, headers, _ = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "username": "404",
            "original_id": "ABC",
            "source": submission.source.name,
            "url": "https://example.com",
            "text": "test content",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_create_no_original_id(self, client: Client) -> None:
        """Test whether a creation without a original ID is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "username": user.username,
            "source": submission.source.name,
            "url": "https://example.com",
            "text": "test content",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_source(self, client: Client) -> None:
        """Test whether a creation without a source is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "original_id": "base_id",
            "username": user.username,
            "url": "https://example.com",
            "text": "test content",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_transcription_url(self, client: Client) -> None:
        """Test whether a creation without a transcription URL is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
            "text": "test content",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_transcription_text(self, client: Client) -> None:
        """Test whether a creation without a transcription text is caught correctly."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "original_id": "ABC",
            "username": user.username,
            "source": submission.source.name,
            "url": "https://example.com",
        }
        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_with_blacklisted_user(self, client: Client) -> None:
        """Test whether a creation with a blacklisted user is rejected."""
        client, headers, user = setup_user_client(client)
        user.blacklisted = True
        user.save()

        submission = create_submission()
        data = {
            "submission_id": submission.id,
            "username": user.username,
            "original_id": "ABC",
            "source": submission.source.name,
            "url": "https://example.com",
            "text": "test content",
        }

        result = client.post(
            reverse("transcription-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_423_LOCKED
        assert Transcription.objects.count() == 0


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
            reverse("transcription-search") + f"?submission_id={first_sub.id}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()) == 1
        assert result.json()[0]["id"] == transcription.id

    def test_search_nonexistent_id(self, client: Client) -> None:
        """Test whether no items are returned when a search on a nonexistent ID is run."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("transcription-search") + "?submission_id=404",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert not result.json()

    def test_search_no_original_id(self, client: Client) -> None:
        """Check whether a search without ID is caught correctly."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("transcription-search"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "ordering,create_times,expected_times",
        [
            (
                "create_time",
                [
                    datetime(2021, 12, 1, 11, 13, 16),
                    datetime(2021, 6, 1, 11, 13, 14),
                    datetime(2021, 6, 1, 11, 13, 15),
                    datetime(2021, 5, 1, 11, 13, 14),
                    datetime(2021, 7, 1, 11, 10, 14),
                ],
                [
                    datetime(2021, 5, 1, 11, 13, 14),
                    datetime(2021, 6, 1, 11, 13, 14),
                    datetime(2021, 6, 1, 11, 13, 15),
                    datetime(2021, 7, 1, 11, 10, 14),
                    datetime(2021, 12, 1, 11, 13, 16),
                ],
            ),
            (
                "-create_time",
                [
                    datetime(2021, 12, 1, 11, 13, 16),
                    datetime(2021, 6, 1, 11, 13, 14),
                    datetime(2021, 6, 1, 11, 13, 15),
                    datetime(2021, 5, 1, 11, 13, 14),
                    datetime(2021, 7, 1, 11, 10, 14),
                ],
                [
                    datetime(2021, 12, 1, 11, 13, 16),
                    datetime(2021, 7, 1, 11, 10, 14),
                    datetime(2021, 6, 1, 11, 13, 15),
                    datetime(2021, 6, 1, 11, 13, 14),
                    datetime(2021, 5, 1, 11, 13, 14),
                ],
            ),
        ],
    )
    def test_search_with_ordering_filter(
        self,
        client: Client,
        ordering: str,
        create_times: List[datetime],
        expected_times: List[datetime],
    ) -> None:
        """Verify that listing items with specified orderings works correctly."""
        client, headers, user = setup_user_client(client)

        for time in create_times:
            create_transcription(
                create_time=make_aware(time), submission=create_submission(), user=user
            )

        result = client.get(
            reverse("transcription-list") + f"?ordering={ordering}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK

        result_times = [
            datetime.strptime(obj.get("create_time"), "%Y-%m-%dT%H:%M:%SZ")
            for obj in result.json()["results"]
        ]
        assert result_times == expected_times


class TestTranscriptionRandom:
    """Tests that validate the behavior of the Random Review process."""

    def test_random_none_available(self, client: Client) -> None:
        """Test that no transcription is returned when there is none available."""
        client, headers, user = setup_user_client(client)
        result = client.get(reverse("transcription-review-random"), **headers)

        assert not result.content
        assert result.status_code == status.HTTP_200_OK

    def test_random(self, client: Client) -> None:
        """Test whether a transcription is returned when available."""
        client, headers, user = setup_user_client(client)
        submission = create_submission()
        transcription = create_transcription(submission, user)

        result = client.get(reverse("transcription-review-random"), **headers)

        assert result.status_code == status.HTTP_200_OK
        assert result.json()
        assert result.json()["original_id"] == transcription.original_id
