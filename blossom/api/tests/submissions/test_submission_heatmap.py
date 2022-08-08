from datetime import datetime

from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status

from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)


class TestHeatmap:
    """Tests to validate that the heatmap data is generated correctly."""

    def test_heatmap_time_slots(self, client: Client) -> None:
        """Test that the time slots are assigned as expected."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        dates = [
            # Thursday 14 h
            datetime(2020, 7, 16, 14, 3, 55),
            # Sunday 15 h
            datetime(2021, 6, 20, 15, 10, 5),
            # Wednesday 03 h
            datetime(2021, 6, 23, 3, 16, 30),
            # Saturday 21 h
            datetime(2021, 6, 26, 21, 1, 10),
        ]

        for date in dates:
            create_submission(completed_by=user, complete_time=date)

        result = client.get(
            reverse("submission-heatmap") + "?completed_by=123456",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_heatmap = [
            # Wednesday 03 h
            {"day": 3, "hour": 3, "count": 1},
            # Thursday 14 h
            {"day": 4, "hour": 14, "count": 1},
            # Saturday 21 h
            {"day": 6, "hour": 21, "count": 1},
            # Sunday 15 h
            {"day": 7, "hour": 15, "count": 1},
        ]
        heatmap = result.json()
        assert heatmap == expected_heatmap

    def test_heatmap_aggregation(self, client: Client) -> None:
        """Test that transcriptions in the same slot are aggregated."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        dates = [
            # Thursday 14 h
            datetime(2020, 7, 16, 14, 3, 55),
            # Thursday 14 h
            datetime(2020, 7, 16, 14, 59, 55),
            # Sunday 15 h
            datetime(2021, 6, 20, 15, 10, 5),
            # Sunday 15 h
            datetime(2021, 6, 20, 15, 42, 10),
            # Sunday 16 h
            datetime(2021, 6, 20, 16, 5, 5),
            # Thursday 14 h
            datetime(2021, 6, 24, 14, 30, 30),
        ]

        for date in dates:
            create_transcription(
                create_submission(completed_by=user, complete_time=make_aware(date)),
                user,
                create_time=make_aware(date),
            )

        result = client.get(
            reverse("submission-heatmap") + "?completed_by=123456",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_heatmap = [
            # Thursday 14 h
            {"day": 4, "hour": 14, "count": 3},
            # Sunday 15 h
            {"day": 7, "hour": 15, "count": 2},
            # Sunday 16 h
            {"day": 7, "hour": 16, "count": 1},
        ]
        heatmap = result.json()
        assert heatmap == expected_heatmap

    def test_heatmap_timezones(self, client: Client) -> None:
        """Test that the timezone is adjusted correctly, if specified."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        dates = [
            # Thursday 14:03 h
            datetime(2020, 7, 16, 14, 3, 55),
            # Thursday 14:59 h
            datetime(2020, 7, 16, 14, 59, 55),
            # Sunday 15:10 h
            datetime(2021, 6, 20, 15, 10, 5),
            # Sunday 15:42 h
            datetime(2021, 6, 20, 15, 42, 10),
            # Sunday 16:05 h
            datetime(2021, 6, 20, 16, 5, 5),
            # Thursday 14:30 h
            datetime(2021, 6, 24, 14, 30, 30),
        ]

        for date in dates:
            create_transcription(
                create_submission(completed_by=user, complete_time=make_aware(date)),
                user,
                create_time=make_aware(date),
            )

        # +01:30 offset
        utc_offset = 90 * 60

        result = client.get(
            reverse("submission-heatmap")
            + f"?completed_by=123456&utc_offset={utc_offset}",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_heatmap = [
            # Thursday 13:30 - 14:30 UTC
            {"day": 4, "hour": 15, "count": 1},
            # Thursday 14:30 - 15:30 UTC
            {"day": 4, "hour": 16, "count": 2},
            # Sunday 14:30 - 15:30 UTC
            {"day": 7, "hour": 16, "count": 1},
            # Sunday 15:30 - 16:30 UTC
            {"day": 7, "hour": 17, "count": 2},
        ]
        heatmap = result.json()
        assert heatmap == expected_heatmap

    def test_heatmap_filtering(self, client: Client) -> None:
        """Verify that filters can be applied to the submissions."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        dates = [
            # Thursday 14 h
            datetime(2020, 7, 16, 14, 3, 55),
            # Thursday 14 h
            datetime(2020, 7, 16, 14, 59, 55),
            # Sunday 15 h
            datetime(2021, 6, 20, 15, 10, 5),
            # Sunday 15 h
            datetime(2021, 6, 20, 15, 42, 10),
            # Sunday 16 h
            datetime(2021, 6, 20, 16, 5, 5),
            # Thursday 14 h
            datetime(2021, 6, 24, 14, 30, 30),
        ]

        for date in dates:
            create_transcription(
                create_submission(completed_by=user, complete_time=make_aware(date)),
                user,
                create_time=make_aware(date),
            )

        result = client.get(
            reverse("submission-heatmap")
            + "?complete_time__gte=2021-06-19T00:00:00Z"
            + "&complete_time__lte=2021-06-21T00:00:00Z",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_heatmap = [
            # Sunday 15 h
            {"day": 7, "hour": 15, "count": 2},
            # Sunday 16 h
            {"day": 7, "hour": 16, "count": 1},
        ]
        heatmap = result.json()
        assert heatmap == expected_heatmap
