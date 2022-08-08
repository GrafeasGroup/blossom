from datetime import datetime
from typing import Dict, List, Union

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status

from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)


class TestSubmissionRate:
    """Tests to validate the behavior of the rate calculation."""

    @pytest.mark.parametrize(
        "data,url_additions,different_result",
        [
            (
                [
                    {"count": 2, "date": "2021-06-15T00:00:00Z"},
                    {"count": 4, "date": "2021-06-16T00:00:00Z"},
                    {"count": 1, "date": "2021-06-17T00:00:00Z"},
                ],
                None,
                None,
            ),
            (
                [
                    {"count": 20, "date": "2021-06-15T00:00:00Z"},
                    {"count": 40, "date": "2021-06-16T00:00:00Z"},
                    {"count": 10, "date": "2021-06-17T00:00:00Z"},
                ],
                None,
                None,
            ),
            (
                [
                    {"count": 2, "date": "2021-06-10T00:00:00Z"},
                    {"count": 2, "date": "2021-06-11T00:00:00Z"},
                ],
                "?page_size=1",
                [{"count": 2, "date": "2021-06-10T00:00:00Z"}],
            ),
            (
                [
                    {"count": 1, "date": "2021-06-10T00:00:00Z"},
                    {"count": 2, "date": "2021-06-11T00:00:00Z"},
                    {"count": 3, "date": "2021-06-12T00:00:00Z"},
                ],
                "?page_size=1&page=2",
                [{"count": 2, "date": "2021-06-11T00:00:00Z"}],
            ),
            (
                [
                    {"count": 1, "date": "2021-06-10T00:00:00Z"},
                    {"count": 2, "date": "2021-06-11T00:00:00Z"},
                    {"count": 3, "date": "2021-06-12T00:00:00Z"},
                ],
                "?page_size=2&page=1",
                [
                    {"count": 1, "date": "2021-06-10T00:00:00Z"},
                    {"count": 2, "date": "2021-06-11T00:00:00Z"},
                ],
            ),
        ],
    )
    def test_rate_count_aggregation(
        self,
        client: Client,
        data: List[Dict[str, Union[str, int]]],
        url_additions: str,
        different_result: List[Dict],
    ) -> None:
        """Test if the number of transcriptions per day is aggregated correctly."""
        client, headers, user = setup_user_client(client, id=123456)

        for obj in data:
            date = make_aware(datetime.strptime(obj.get("date"), "%Y-%m-%dT%H:%M:%SZ"))
            for _ in range(obj.get("count")):
                create_transcription(
                    create_submission(completed_by=user, complete_time=date),
                    user,
                    create_time=date,
                )
        if not url_additions:
            url_additions = "?completed_by=123456"
        else:
            url_additions += "&completed_by=123456"
        result = client.get(
            reverse("submission-rate") + url_additions,
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        rates = result.json()["results"]
        if different_result:
            assert rates == different_result
        else:
            assert rates == data

    def test_pagination(self, client: Client) -> None:
        """Verify that pagination parameters properly change response."""
        client, headers, user = setup_user_client(client, id=123456)
        for day in range(1, 4):
            date = make_aware(datetime(2021, 6, day))
            create_transcription(
                create_submission(completed_by=user, complete_time=date),
                user,
                create_time=date,
            )
        result = client.get(
            reverse("submission-rate") + "?page_size=1&page=2&completed_by=123456",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        response = result.json()
        assert len(response["results"]) == 1
        assert response["results"][0]["date"] == "2021-06-02T00:00:00Z"
        assert response["previous"] is not None
        assert response["next"] is not None

    @pytest.mark.parametrize(
        "time_frame,dates,results",
        [
            (
                "none",
                [
                    datetime(2021, 6, 1, 11, 13, 14),
                    datetime(2021, 6, 1, 11, 13, 15),
                    datetime(2021, 6, 1, 11, 13, 16),
                    datetime(2022, 6, 1, 11, 13, 14),
                    datetime(2022, 7, 1, 11, 10, 14),
                ],
                [
                    {"count": 1, "date": "2021-06-01T11:13:14Z"},
                    {"count": 1, "date": "2021-06-01T11:13:15Z"},
                    {"count": 1, "date": "2021-06-01T11:13:16Z"},
                    {"count": 1, "date": "2022-06-01T11:13:14Z"},
                    {"count": 1, "date": "2022-07-01T11:10:14Z"},
                ],
            ),
            (
                "hour",
                [
                    datetime(2021, 6, 1, 11),
                    datetime(2021, 6, 1, 12, 10),
                    datetime(2021, 6, 1, 12, 20),
                    datetime(2021, 6, 1, 12, 25),
                    datetime(2022, 6, 1, 10),
                    datetime(2022, 7, 1, 12),
                ],
                [
                    {"count": 1, "date": "2021-06-01T11:00:00Z"},
                    {"count": 3, "date": "2021-06-01T12:00:00Z"},
                    {"count": 1, "date": "2022-06-01T10:00:00Z"},
                    {"count": 1, "date": "2022-07-01T12:00:00Z"},
                ],
            ),
            (
                "day",
                [
                    datetime(2021, 6, 1, 11),
                    datetime(2021, 6, 1, 12),
                    datetime(2022, 6, 1, 10),
                    datetime(2022, 7, 1, 12),
                ],
                [
                    {"count": 2, "date": "2021-06-01T00:00:00Z"},
                    {"count": 1, "date": "2022-06-01T00:00:00Z"},
                    {"count": 1, "date": "2022-07-01T00:00:00Z"},
                ],
            ),
            (
                "week",
                [
                    datetime(2021, 6, 1, 11),
                    datetime(2021, 6, 1, 12),
                    datetime(2021, 6, 3, 12),
                    datetime(2021, 6, 6, 12),
                    datetime(2022, 6, 1, 10),
                    datetime(2022, 7, 1, 12),
                ],
                [
                    {"count": 4, "date": "2021-05-31T00:00:00Z"},
                    {"count": 1, "date": "2022-05-30T00:00:00Z"},
                    {"count": 1, "date": "2022-06-27T00:00:00Z"},
                ],
            ),
            (
                "month",
                [
                    datetime(2021, 6, 1, 11),
                    datetime(2021, 6, 1, 12),
                    datetime(2021, 6, 3, 12),
                    datetime(2021, 6, 6, 12),
                    datetime(2022, 6, 1, 10),
                    datetime(2022, 6, 10, 10),
                    datetime(2022, 6, 25, 10),
                    datetime(2022, 6, 30, 10),
                    datetime(2022, 7, 1, 12),
                ],
                [
                    {"count": 4, "date": "2021-06-01T00:00:00Z"},
                    {"count": 4, "date": "2022-06-01T00:00:00Z"},
                    {"count": 1, "date": "2022-07-01T00:00:00Z"},
                ],
            ),
            (
                "year",
                [
                    datetime(2021, 6, 1, 11),
                    datetime(2021, 6, 1, 12),
                    datetime(2021, 6, 3, 12),
                    datetime(2021, 6, 6, 12),
                    datetime(2022, 6, 1, 10),
                    datetime(2022, 6, 10, 10),
                    datetime(2022, 6, 25, 10),
                    datetime(2022, 6, 30, 10),
                    datetime(2022, 7, 1, 12),
                    datetime(2022, 10, 1, 12),
                ],
                [
                    {"count": 4, "date": "2021-01-01T00:00:00Z"},
                    {"count": 6, "date": "2022-01-01T00:00:00Z"},
                ],
            ),
        ],
    )
    def test_time_frames(
        self,
        client: Client,
        time_frame: str,
        dates: List[datetime],
        results: List[Dict[str, Union[str, int]]],
    ) -> None:
        """Verify that the time_frame parameter properly changes the response."""
        client, headers, user = setup_user_client(client, id=123456)

        for date in dates:
            create_transcription(
                create_submission(completed_by=user, complete_time=date),
                user,
                create_time=make_aware(date),
            )

        result = client.get(
            reverse("submission-rate")
            + f"?time_frame={time_frame}&completed_by=123456",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        response = result.json()
        assert response["results"] == results

    def test_rate_filtering(
        self,
        client: Client,
    ) -> None:
        """Verify that filters can be applied to the submissions."""
        client, headers, user = setup_user_client(client, id=123456)

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
                create_submission(completed_by=user, complete_time=date),
                user,
                create_time=make_aware(date),
            )

        result = client.get(
            reverse("submission-rate")
            + "?time_frame=day&completed_by=123456"
            + "&complete_time__gte=2021-06-01T00:00:00Z"
            + "&complete_time__lte=2021-06-21T00:00:00Z",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        response = result.json()
        assert response["results"] == [
            {"count": 3, "date": "2021-06-20T00:00:00Z"},
        ]

    def test_rate_timezones(
        self,
        client: Client,
    ) -> None:
        """Verify that the timezone is applied correctly, if specified."""
        client, headers, user = setup_user_client(client, id=123456)

        dates = [
            # 2020-07-16 23:00 UTC
            datetime(2020, 7, 16, 23),
            # 2020-07-16 22:00 UTC
            datetime(2020, 7, 16, 22),
        ]

        for date in dates:
            create_transcription(
                create_submission(completed_by=user, complete_time=date),
                user,
                create_time=make_aware(date),
            )

        # +01:30 offset
        utc_offset = 90 * 60

        result = client.get(
            reverse("submission-rate")
            + "?time_frame=day&completed_by=123456"
            + f"&utc_offset={utc_offset}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        response = result.json()
        assert response["results"] == [
            {"count": 1, "date": "2020-07-16T00:00:00+01:30"},
            {"count": 1, "date": "2020-07-17T00:00:00+01:30"},
        ]
