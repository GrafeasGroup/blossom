import datetime

from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.models import Source
from api.tests.helpers import create_submission, setup_user_client


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

    def test_list_with_time_filters(self, client: Client) -> None:
        """Verify that listing submissions using time filters works correctly."""
        client, headers, _ = setup_user_client(client)

        create_submission(
            complete_time=timezone.make_aware(datetime.datetime(2021, 1, 1))
        )
        create_submission(
            complete_time=timezone.make_aware(datetime.datetime(2021, 1, 2))
        )
        create_submission(
            complete_time=timezone.make_aware(datetime.datetime(2021, 1, 3))
        )
        create_submission(
            complete_time=timezone.make_aware(datetime.datetime(2021, 1, 4))
        )

        result = client.get(
            reverse("submission-list") + "?from=2021-01-02,1pm",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 2

        result = client.get(
            reverse("submission-list") + "?from=2021-01-03",
            content_type="application/json",
            **headers,
        )
        assert len(result.json()["results"]) == 1

        result = client.get(
            reverse("submission-list") + "?from=2020-12-31&until=2021-01-05",
            content_type="application/json",
            **headers,
        )
        assert len(result.json()["results"]) == 4

    def test_list_with_advanced_time_filters(self, client: Client) -> None:
        """Verify that listing items with English time filters works properly."""
        client, headers, _ = setup_user_client(client)
        today = timezone.now()

        create_submission(complete_time=today - timezone.timedelta(hours=6))
        create_submission(complete_time=today - timezone.timedelta(days=1))
        create_submission(complete_time=today - timezone.timedelta(days=2))
        create_submission(complete_time=today - timezone.timedelta(days=3))
        create_submission(complete_time=today - timezone.timedelta(days=4))

        result = client.get(
            reverse("submission-list") + "?from=yesterday",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        # should just be the one from 6 hours ago
        assert len(result.json()["results"]) == 1

        result = client.get(
            reverse("submission-list") + "?from=day%20before%20yesterday",
            content_type="application/json",
            **headers,
        )
        assert len(result.json()["results"]) == 2

        result = client.get(
            reverse("submission-list")
            + "?from=day%20before%20yesterday&until=yesterday",
            content_type="application/json",
            **headers,
        )
        assert len(result.json()["results"]) == 1

        result = client.get(
            reverse("submission-list") + "?from=aaaaaaaaaa",
            content_type="application/json",
            **headers,
        )
        assert len(result.json()["results"]) == 5
