from typing import Dict, List, Union

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.tests.helpers import (
    create_submission,
    create_user,
    setup_user_client,
)

class TestSubmissionLeaderboard:
    """Tests to validate the behavior of the leaderboard creation."""

    UserData = Dict[str, Union[str, int]]

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
        """Test if the number of transcriptions per day is aggregated correctly."""
        client, headers, _ = setup_user_client(client, id=99999, is_volunteer=False)

        for obj in data:
            user_id = obj.get("id")
            cur_user = create_user(id=user_id, username=f"user-{user_id}", is_volunteer=True)
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
                    {"id": 3, "gamma": 15},
                ],
                1,
                [{"id": 3, "gamma": 15, "rank": 1, "username": "user-3"}],
                {"id": 1, "gamma": 10, "rank": 2, "username": "user-1"},
                [{"id": 2, "gamma": 4, "rank": 3, "username": "user-2"}],
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
        """Test if the number of transcriptions per day is aggregated correctly."""
        client, headers, _ = setup_user_client(client, id=99999, is_volunteer=False)

        for obj in data:
            cur_user_id = obj.get("id")
            cur_user = create_user(id=cur_user_id, username=f"user-{cur_user_id}", is_volunteer=True)
            for _ in range(obj.get("gamma")):
                create_submission(completed_by=cur_user)

        result = client.get(
            reverse("submission-leaderboard") + f"?user_id={user_id}",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        actual_user = result.json()["user"]
        assert actual_user == expected_user
        actual_above = result.json()["above"]
        assert actual_above == expected_above
        actual_below = result.json()["below"]
        assert actual_below == actual_below
