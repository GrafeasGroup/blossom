from datetime import datetime
from typing import Dict, List, Union

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status

from api.tests.helpers import (
    create_submission,
    create_user,
    setup_user_client,
)


class TestSubmissionLeaderboard:
    """Tests to validate the behavior of the leaderboard creation."""

    UserData = Dict[str, Union[str, int, datetime]]

    @pytest.mark.parametrize(
        "data,expected",
        [
            (
                [
                    {"id": 1, "gamma": 10},
                    {"id": 2, "gamma": 4},
                    {"id": 3, "gamma": 15},
                ],
                [
                    {"id": 3, "gamma": 15, "rank": 1, "username": "user-3"},
                    {"id": 1, "gamma": 10, "rank": 2, "username": "user-1"},
                    {"id": 2, "gamma": 4, "rank": 3, "username": "user-2"},
                ],
            )
        ],
    )
    def test_top_leaderboard(
        self, client: Client, data: List[UserData], expected: List[UserData],
    ) -> None:
        """Test if the top leaderboard is set up correctly."""
        client, headers, _ = setup_user_client(client, id=99999, is_volunteer=False)

        for obj in data:
            user_id = obj.get("id")
            cur_user = create_user(
                id=user_id, username=f"user-{user_id}", is_volunteer=True,
            )
            for _ in range(obj.get("gamma")):
                create_submission(completed_by=cur_user)

        result = client.get(
            reverse("submission-leaderboard"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        actual = result.json()["top"]
        assert actual == expected

    @pytest.mark.parametrize(
        "data,user_id,expected_above,expected_user,expected_below",
        [
            (
                [
                    {"id": 1, "gamma": 10},
                    {"id": 2, "gamma": 4},
                    {"id": 3, "gamma": 15, "date_joined": datetime(2021, 11, 3)},
                    {"id": 4, "gamma": 15, "date_joined": datetime(2021, 11, 4)},
                ],
                1,
                [
                    {"id": 4, "gamma": 15, "rank": 1, "username": "user-4"},
                    {"id": 3, "gamma": 15, "rank": 2, "username": "user-3"},
                ],
                {"id": 1, "gamma": 10, "rank": 3, "username": "user-1"},
                [{"id": 2, "gamma": 4, "rank": 4, "username": "user-2"}],
            )
        ],
    )
    def test_user_leaderboard(
        self,
        client: Client,
        data: List[UserData],
        user_id: int,
        expected_above: List[UserData],
        expected_user: UserData,
        expected_below: List[UserData],
    ) -> None:
        """Test if the user related leaderboard is set up correctly."""
        client, headers, _ = setup_user_client(client, id=99999, is_volunteer=False)

        for obj in data:
            cur_user_id = obj.get("id")
            date_joined = make_aware(obj.get("date_joined", datetime.now()))
            cur_user = create_user(
                id=cur_user_id,
                username=f"user-{cur_user_id}",
                is_volunteer=True,
                date_joined=date_joined,
            )
            for _ in range(obj.get("gamma")):
                create_submission(completed_by=cur_user)

        results = client.get(
            reverse("submission-leaderboard") + f"?user_id={user_id}",
            content_type="application/json",
            **headers,
        )

        assert results.status_code == status.HTTP_200_OK
        results = results.json()
        actual_user = results["user"]
        assert actual_user == expected_user
        actual_above = results["above"]
        assert actual_above == expected_above
        actual_below = results["below"]
        assert actual_below == actual_below

    def test_filtered_leaderboard(self, client: Client,) -> None:
        """Test if the submissions for the rate is calculated on are filtered."""
        client, headers, user = setup_user_client(
            client, id=1, username="user-1", is_volunteer=False
        )

        # Submissions before filter
        for _ in range(4):
            create_submission(
                completed_by=user, complete_time=make_aware(datetime(2021, 11, 3))
            )
        # Submissions after filter
        for _ in range(7):
            create_submission(
                completed_by=user, complete_time=make_aware(datetime(2021, 11, 5))
            )

        results = client.get(
            reverse("submission-leaderboard") + "?user_id=1&from=2021-11-04",
            content_type="application/json",
            **headers,
        )

        assert results.status_code == status.HTTP_200_OK
        results = results.json()
        assert results["user"] == {
            "id": 1,
            "username": "user-1",
            "gamma": 7,
            "rank": 1,
        }
