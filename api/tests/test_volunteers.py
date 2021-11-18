"""Tests to validate the behavior of the VolunteerViewSet."""
import json
from datetime import datetime
from typing import Dict, List, Union

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status

from api.models import Submission, Transcription
from api.tests.helpers import (
    create_submission,
    create_transcription,
    create_user,
    setup_user_client,
)
from authentication.models import BlossomUser


class TestVolunteerSummary:
    """Tests to validate the behavior of the summary process."""

    def test_summary(self, client: Client) -> None:
        """Test whether the process functions correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("volunteer-summary") + f"?username={user.username}", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json().get("username") == user.username
        assert result.json()["id"] == user.id

    def test_summary_no_username(self, client: Client) -> None:
        """Test whether the summary is not provided when no username is queried."""
        client, headers, _ = setup_user_client(client)
        result = client.get(reverse("volunteer-summary"), **headers)
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_summary_nonexistent_username(self, client: Client) -> None:
        """Test whether the summary is not given when a nonexistent user is provided."""
        client, headers, _ = setup_user_client(client)
        result = client.get(reverse("volunteer-summary") + "?username=404", **headers)
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_summary_blacklisted_user(self, client: Client) -> None:
        """Test that a blacklisted user is reported as having 0 gamma."""
        client, headers, user = setup_user_client(client)
        user.blacklisted = True
        user.save()

        for _ in range(3):
            create_submission(completed_by=user)

        assert Submission.objects.filter(completed_by=user).count() == 3

        result = client.get(
            reverse("volunteer-summary") + f"?username={user.username}", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json().get("username") == user.username
        assert result.json()["gamma"] == 0

        user.blacklisted = False
        user.save()

        result = client.get(
            reverse("volunteer-summary") + f"?username={user.username}", **headers
        )

        assert result.json()["gamma"] == 3


class TestVolunteerRate:
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
            for _ in range(obj.get("count")):
                create_transcription(
                    create_submission(),
                    user,
                    create_time=make_aware(
                        datetime.strptime(obj.get("date"), "%Y-%m-%dT%H:%M:%SZ")
                    ),
                )
        if not url_additions:
            url_additions = ""
        result = client.get(
            reverse("volunteer-rate", kwargs={"pk": 123456}) + url_additions,
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
            create_transcription(
                create_submission(),
                user,
                create_time=make_aware(datetime(2021, 6, day)),
            )
        result = client.get(
            reverse("volunteer-rate", kwargs={"pk": 123456}) + "?page_size=1&page=2",
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
                create_submission(), user, create_time=make_aware(date),
            )

        result = client.get(
            reverse("volunteer-rate", kwargs={"pk": 123456})
            + f"?time_frame={time_frame}",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        response = result.json()
        assert response["results"] == results


class TestVolunteerAssortedFunctions:
    """Tests to validate the behavior of miscellaneous functions."""

    def test_list(self, client: Client) -> None:
        """Verify that getting the list of users works correctly."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("volunteer-list"), content_type="application/json", **headers
        )
        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 1
        assert result.json()["results"][0]["username"] == user.username

        create_user(email="a@a.com", username="AAA")

        result = client.get(
            reverse("volunteer-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 2
        assert result.json()["results"][1]["username"] == "AAA"

    def test_list_with_filters(self, client: Client) -> None:
        """Verify that listing all submissions works correctly."""
        client, headers, user = setup_user_client(client)

        create_user(username="A")
        create_user(username="B")
        create_user(username="C")
        create_user(username="D")

        result = client.get(
            reverse("volunteer-list"), content_type="application/json", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 5

        result = client.get(
            reverse("volunteer-list") + "?username=C",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert result.json()["results"][0]["username"] == "C"

        result = client.get(
            reverse("volunteer-list") + "?username=C&id=1",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 0

    def test_edit_volunteer(self, client: Client) -> None:
        """Test whether an edit of a user is propagated correctly."""
        client, headers, user = setup_user_client(client)
        data = {"username": "naaaarf"}
        result = client.put(
            reverse("volunteer-detail", args=[1]),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        user.refresh_from_db()
        assert result.status_code == status.HTTP_200_OK
        assert result.json()["username"] == data["username"]
        assert user.username == data["username"]

    def test_volunteer_viewset_with_qsp(self, client: Client) -> None:
        """Test whether querying with a username provides the specific user."""
        client, headers, user = setup_user_client(client)
        create_user(username="another_user")
        result = client.get(
            reverse("volunteer-list") + f"?username={user.username}", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert result.json()["results"][0]["username"] == user.username


class TestVolunteerGammaPlusOne:
    """Tests to validate the behavior of the plus one process."""

    def test_plus_one(self, client: Client) -> None:
        """Test whether an artificial gamma is provided when invoked correctly."""
        client, headers, user = setup_user_client(client)

        result = client.patch(
            reverse("volunteer-gamma-plusone", args=[user.id]), **headers
        )

        user.refresh_from_db()
        assert result.status_code == status.HTTP_200_OK
        assert result.json()["gamma"] == 1
        assert user.gamma == 1
        assert Transcription.objects.count() == 1
        assert Submission.objects.count() == 1
        assert (
            Transcription.objects.get(id=1).author
            == Submission.objects.get(id=1).completed_by
            == user
        )

    def test_plus_one_nonexistent_id(self, client: Client) -> None:
        """Test whether a plus one with a nonexistent ID is caught correctly."""
        client, headers, _ = setup_user_client(client)

        result = client.patch(reverse("volunteer-gamma-plusone", args=[404]), **headers)

        assert result.status_code == status.HTTP_404_NOT_FOUND
        # shouldn't have created anything
        assert Transcription.objects.count() == 0
        assert Submission.objects.count() == 0


class TestVolunteerCreation:
    """Tests to validate the behavior of the user creation."""

    def test_create(self, client: Client) -> None:
        """Test whether a user is successfully created when invoked correctly."""
        client, headers, _ = setup_user_client(client)
        data = {"username": "SPAAAACE"}
        result = client.post(
            reverse("volunteer-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_201_CREATED
        created = BlossomUser.objects.get(id=result.json()["id"])
        assert created.username == data["username"]

    def test_create_duplicate_username(self, client: Client) -> None:
        """Test that no user is created when an user with the username already exists."""
        client, headers, _ = setup_user_client(client)
        data = {"username": "janeeyre"}
        create_user(username=data["username"])

        result = client.post(
            reverse("volunteer-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert BlossomUser.objects.filter(username=data["username"]).count() == 1

    def test_create_no_username(self, client: Client) -> None:
        """Test that no user is created when no username is provided."""
        client, headers, _ = setup_user_client(client)

        result = client.post(
            reverse("volunteer-list"), content_type="application/json", **headers
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST
        assert BlossomUser.objects.count() == 1


class TestVolunteerCoCAcceptance:
    """Tests to validate that accepting the CoC works correctly."""

    def test_accept_coc(self, client: Client) -> None:
        """Test that a correctly formatted request succeeds."""
        client, headers, user = setup_user_client(client, accepted_coc=False)

        assert user.accepted_coc is False
        result = client.post(
            reverse("volunteer-accept-coc") + f"?username={user.username}", **headers
        )

        assert result.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.accepted_coc is True

    def test_accept_coc_invalid_user(self, client: Client) -> None:
        """Test that an operation on an invalid volunteer fails as expected."""
        client, headers, user = setup_user_client(client, accepted_coc=False)

        assert user.accepted_coc is False
        result = client.post(
            reverse("volunteer-accept-coc") + "?username=AAAAAAAAA", **headers
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND
        user.refresh_from_db()
        assert user.accepted_coc is False

    def test_accept_coc_duplicate(self, client: Client) -> None:
        """Test that a 409 is returned when endpoint is called twice on same user."""
        client, headers, user = setup_user_client(client, accepted_coc=True)

        result = client.post(
            reverse("volunteer-accept-coc") + f"?username={user.username}", **headers
        )
        assert result.status_code == status.HTTP_409_CONFLICT
        user.refresh_from_db()
        assert user.accepted_coc is True


class TestHeatmap:
    """Tests to validate that the heatmap data is generated correctly."""

    def test_heatmap_time_slots(self, client: Client) -> None:
        """Test that the time slots are assigned as expected."""
        client, headers, user = setup_user_client(
            client, accepted_coc=True, username="test_user"
        )

        # Thursday 14 h
        create_transcription(
            create_submission(), user, create_time=datetime(2020, 7, 16, 14, 3, 55)
        )
        # Sunday 15 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 20, 15, 10, 5)
        )
        # Wednesday 03 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 23, 3, 16, 30)
        )
        # Saturday 21 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 26, 21, 1, 10)
        )

        result = client.get(
            reverse("volunteer-heatmap") + "?username=test_user",
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
        client, headers, user = setup_user_client(
            client, accepted_coc=True, username="test_user"
        )

        # Thursday 14 h
        create_transcription(
            create_submission(), user, create_time=datetime(2020, 7, 16, 14, 3, 55)
        )
        # Thursday 14 h
        create_transcription(
            create_submission(), user, create_time=datetime(2020, 7, 16, 14, 59, 55)
        )
        # Sunday 15 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 20, 15, 10, 5)
        )
        # Sunday 15 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 20, 15, 42, 10)
        )
        # Sunday 16 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 20, 16, 5, 5)
        )
        # Thursday 14 h
        create_transcription(
            create_submission(), user, create_time=datetime(2021, 6, 24, 14, 30, 30)
        )

        result = client.get(
            reverse("volunteer-heatmap") + "?username=test_user",
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
