"""Tests to validate the behavior of the VolunteerViewSet."""
import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.models import Submission, Transcription
from api.tests.helpers import create_user, setup_user_client
from authentication.models import BlossomUser


class TestVolunteerSummary:
    """Tests to validate the behavior of the summary process."""

    def test_summary(self, client: Client) -> None:
        """Test whether the process functions correctly when invoked correctly."""
        client, headers, user = setup_user_client(client)
        result = client.get(
            reverse("volunteer-summary") + f"?username={user.username}", **headers,
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
        result = client.get(reverse("volunteer-summary") + "?username=404", **headers,)
        assert result.status_code == status.HTTP_404_NOT_FOUND


class TestVolunteerAssortedFunctions:
    """Tests to validate the behavior of miscellaneous functions."""

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
            reverse("volunteer-list") + f"?username={user.username}", **headers,
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
            reverse("volunteer-gamma-plusone", args=[user.id]), **headers,
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

        result = client.patch(
            reverse("volunteer-gamma-plusone", args=[404]), **headers,
        )

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
            reverse("volunteer-list"), content_type="application/json", **headers,
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
            reverse("volunteer-accept-coc", args=[user.id]),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.accepted_coc is True

    def test_accept_coc_invalid_user(self, client: Client) -> None:
        """Test that an operation on an invalid volunteer fails as expected."""
        client, headers, user = setup_user_client(client, accepted_coc=False)

        assert user.accepted_coc is False

        result = client.post(
            reverse("volunteer-accept-coc", args=[999]),
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND
        user.refresh_from_db()
        assert user.accepted_coc is False
