from datetime import datetime
from typing import Any, Dict, List, Union

import pytest
import pytz
from django.test import Client
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status

from blossom.authentication.models import BlossomUser
from blossom.utils.test_helpers import create_submission, create_user, setup_user_client


def extract_ids(results: List[Dict[str, Any]]) -> List[int]:
    """Extract the user IDs from the result set."""
    return [res["id"] for res in results]


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
                [3, 1, 2],
            )
        ],
    )
    def test_top_leaderboard(
        self,
        client: Client,
        data: List[UserData],
        expected: List[UserData],
    ) -> None:
        """Test if the top leaderboard is set up correctly."""
        BlossomUser.objects.all().delete()
        client, headers, _ = setup_user_client(client, id=99999, is_volunteer=False)

        for obj in data:
            user_id = obj.get("id")
            cur_user = create_user(
                id=user_id,
                username=f"user-{user_id}",
                is_volunteer=True,
            )
            for _ in range(obj.get("gamma")):
                create_submission(completed_by=cur_user)

        result = client.get(
            reverse("submission-leaderboard"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        actual = extract_ids(result.json()["top"])
        assert actual == expected

    @pytest.mark.parametrize(
        "data,user_id,expected_above,expected_user,expected_below",
        [
            (
                [
                    {"id": 1, "gamma": 10, "date_joined": datetime(2021, 11, 5)},
                    {"id": 2, "gamma": 4},
                    {"id": 3, "gamma": 15, "date_joined": datetime(2021, 11, 3)},
                    {"id": 4, "gamma": 15, "date_joined": datetime(2021, 11, 4)},
                ],
                1,
                [4, 3],
                {
                    "id": 1,
                    "gamma": 10,
                    "rank": 3,
                    "username": "user-1",
                    "date_joined": "2021-11-05T00:00:00Z",
                },
                [2],
            )
        ],
    )
    def test_user_leaderboard(
        self,
        client: Client,
        data: List[UserData],
        user_id: int,
        expected_above: List[int],
        expected_user: UserData,
        expected_below: List[int],
    ) -> None:
        """Test if the user related leaderboard is set up correctly."""
        BlossomUser.objects.all().delete()
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
        assert results["user"] == expected_user
        assert extract_ids(results["above"]) == expected_above
        assert extract_ids(results["below"]) == expected_below

    def test_filtered_leaderboard(
        self,
        client: Client,
    ) -> None:
        """Test if the submissions for the rate is calculated on are filtered."""
        BlossomUser.objects.all().delete()
        date_joined = datetime(2021, 11, 3, tzinfo=pytz.UTC)
        client, headers, user = setup_user_client(
            client, id=1, username="user-1", date_joined=date_joined, is_volunteer=True
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
            reverse("submission-leaderboard")
            + "?user_id=1&complete_time__gte=2021-11-04T00:00:00Z",
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
            "date_joined": "2021-11-03T00:00:00Z",
        }
