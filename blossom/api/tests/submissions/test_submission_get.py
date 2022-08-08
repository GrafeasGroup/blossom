from datetime import datetime
from typing import List

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import status

from blossom.api.models import Source
from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubmissionGet:
    """Tests validating the behavior of the Submission retrieval process."""

    def test_list(self, client: Client) -> None:
        """Verify that listing all submissions works correctly."""
        client, headers, _ = setup_user_client(client)
        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 0

        submission = create_submission()

        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 1
        assert result.json()["results"][0]["id"] == submission.id

    def test_get_submissions(self, client: Client) -> None:
        """Test whether all current submissions are provided when no args are provided."""
        client, headers, _ = setup_user_client(client)
        first = create_submission()
        second = create_submission(original_id="second")

        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 2
        assert result.json()["results"][0]["id"] == first.id
        assert result.json()["results"][1]["id"] == second.id

    def test_get_specific_id(self, client: Client) -> None:
        """Test whether the specific submission is provided when an ID is supplied."""
        client, headers, _ = setup_user_client(client)
        first = create_submission()
        create_submission(original_id="second")

        result = client.get(
            reverse("submission-list") + f"?original_id={first.original_id}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert result.json()["results"][0]["id"] == first.id

    def test_list_with_filters(self, client: Client) -> None:
        """Verify that listing all submissions works correctly."""
        client, headers, _ = setup_user_client(client)

        aaa, _ = Source.objects.get_or_create(name="AAA")
        bbb, _ = Source.objects.get_or_create(name="BBB")

        create_submission(source=aaa)
        create_submission(source=aaa)
        create_submission(source=bbb)
        create_submission(source=bbb)

        result = client.get(
            reverse("submission-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 4

        result = client.get(
            reverse("submission-list") + "?source=AAA",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 2
        assert "AAA" in result.json()["results"][0]["source"]  # it will be a full link

        result = client.get(
            reverse("submission-list") + "?source=AAA&id=1",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert "AAA" in result.json()["results"][0]["source"]  # it will be a full link
        assert result.json()["results"][0]["id"] == 1

    @pytest.mark.parametrize(
        "time_query,result_count",
        [
            ("complete_time__gt=2021-01-03T00:00:00Z", 1),
            (
                "complete_time__gte=2020-12-31T00:00:00Z"
                "&complete_time__lte=2021-01-05T00:00:00Z",
                4,
            ),
            (
                "complete_time__gte=2021-01-01T12:00:00Z"
                "&complete_time__lte=2021-01-03T12:00:00Z",
                2,
            ),
            (
                "complete_time__gte=2021-01-01T12:00:00Z"
                "&complete_time__lte=2021-01-03T12:00:00Z",
                2,
            ),
            (
                "complete_time__gte=2021-01-01T12:00:00%2b01:00"
                "&complete_time__lte=2021-01-03T12:00:00%2b01:00",
                2,
            ),
            (
                "complete_time__gte=2021-01-01T12:00:00%2b01:00"
                "&complete_time__lte=2021-01-03T12:00:00%2b05:00",
                2,
            ),
        ],
    )
    def test_list_with_time_filters(
        self, client: Client, time_query: str, result_count: int
    ) -> None:
        """Verify that listing submissions using time filters works correctly."""
        client, headers, _ = setup_user_client(client)

        print(f"Time filter test {time_query}")

        create_submission(complete_time=timezone.make_aware(datetime(2021, 1, 1)))
        create_submission(complete_time=timezone.make_aware(datetime(2021, 1, 2)))
        create_submission(complete_time=timezone.make_aware(datetime(2021, 1, 3)))
        create_submission(complete_time=timezone.make_aware(datetime(2021, 1, 4)))

        result = client.get(
            reverse("submission-list") + f"?{time_query}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == result_count

    @pytest.mark.parametrize(
        "ordering,complete_times,expected_times",
        [
            (
                "complete_time",
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
                "-complete_time",
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
    def test_list_with_ordering_filter(
        self,
        client: Client,
        ordering: str,
        complete_times: List[datetime],
        expected_times: List[datetime],
    ) -> None:
        """Verify that listing items with specified orderings works correctly."""
        client, headers, _ = setup_user_client(client)

        for time in complete_times:
            create_submission(complete_time=make_aware(time))

        result = client.get(
            reverse("submission-list") + f"?ordering={ordering}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK

        result_times = [
            datetime.strptime(obj.get("complete_time"), "%Y-%m-%dT%H:%M:%SZ")
            for obj in result.json()["results"]
        ]
        assert result_times == expected_times

    @pytest.mark.parametrize(
        "filter_str,result_count",
        [
            ("claimed_by__isnull=true", 1),
            ("claimed_by__isnull=false", 1),
            ("completed_by__isnull=true", 1),
            ("completed_by__isnull=false", 1),
            ("claim_time__isnull=true", 1),
            ("claim_time__isnull=false", 1),
            ("complete_time__isnull=true", 1),
            ("complete_time__isnull=false", 1),
            ("title__isnull=true", 1),
            ("title__isnull=false", 1),
            ("url__isnull=true", 1),
            ("url__isnull=false", 1),
            ("tor_url__isnull=true", 1),
            ("tor_url__isnull=false", 1),
            ("content_url__isnull=true", 1),
            ("content_url__isnull=false", 1),
        ],
    )
    def test_list_with_null_filters(
        self, client: Client, filter_str: str, result_count: int
    ) -> None:
        """Verify that attributes can be filtered by null."""
        client, headers, user = setup_user_client(client, id=123)
        today = timezone.now()

        create_submission(
            id=1,
            claimed_by=user,
            completed_by=user,
            claim_time=today,
            complete_time=today,
            title="Test Submission",
            url="https://example.org",
            tor_url="https://example.org",
            content_url="https://example.org",
            redis_id="abc",
        )
        create_submission(id=2)

        result = client.get(
            reverse("submission-list") + f"?{filter_str}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == result_count

    @pytest.mark.parametrize(
        "filter_str,result_count",
        [
            ("title__icontains=title", 3),
            ("title__icontains=TITLE", 3),
            ("title__icontains=This", 1),
            ("title__icontains=this", 1),
            ("title__icontains=hamburger", 0),
        ],
    )
    def test_list_with_contains_filters(
        self, client: Client, filter_str: str, result_count: int
    ) -> None:
        """Verify that the title can be searched."""
        client, headers, user = setup_user_client(client, id=123)

        create_submission(
            id=1,
            title="This is a title",
        )
        create_submission(
            id=2,
            title="Another title",
        )
        create_submission(
            id=3,
            title="TITLE IS GOOD",
        )

        result = client.get(
            reverse("submission-list") + f"?{filter_str}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == result_count

    @pytest.mark.parametrize(
        "filter_str,result_count",
        [("removed_from_queue=true", 1), ("removed_from_queue=false", 1), ("", 2)],
    )
    def test_list_with_removed_filter(
        self, client: Client, filter_str: str, result_count: int
    ) -> None:
        """Verify that submissions can be filtered by their removal status."""
        client, headers, user = setup_user_client(client, id=123)

        create_submission(
            id=1,
            removed_from_queue=True,
        )
        create_submission(
            id=2,
            removed_from_queue=False,
        )

        result = client.get(
            reverse("submission-list") + f"?{filter_str}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == result_count
