"""Tests to validate the behavior of the VolunteerViewSet."""
import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.api.models import Submission, Transcription
from blossom.authentication.models import BlossomUser
from blossom.utils.test_helpers import create_submission, create_user, setup_user_client


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

    def test_summary_blocked_user(self, client: Client) -> None:
        """Test that a blocked user is reported as having 0 gamma."""
        client, headers, user = setup_user_client(client)
        user.blocked = True
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

        user.blocked = False
        user.save()

        result = client.get(
            reverse("volunteer-summary") + f"?username={user.username}", **headers
        )

        assert result.json()["gamma"] == 3


class TestVolunteerAssortedFunctions:
    """Tests to validate the behavior of miscellaneous functions."""

    def test_list(self, client: Client) -> None:
        """Verify that getting the list of users works correctly."""
        BlossomUser.objects.all().delete()  # clear out system accounts for test
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
        """Verify that listing all volunteers works correctly."""
        BlossomUser.objects.all().delete()  # clear out system accounts for test
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

    def test_case_insensitive_list_with_filter(self, client: Client) -> None:
        """Verify that listing all volunteers really works correctly."""
        client, headers, user = setup_user_client(client)

        create_user(username="A")

        result = client.get(
            reverse("volunteer-list") + "?username=a",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert len(result.json()["results"]) == 1
        assert result.json()["results"][0]["username"] == "A"

    def test_edit_volunteer(self, client: Client) -> None:
        """Test whether an edit of a user is propagated correctly."""
        client, headers, user = setup_user_client(client)
        data = {"username": "naaaarf"}
        result = client.put(
            reverse("volunteer-detail", args=[5]),
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
        BlossomUser.objects.all().delete()  # clear out system accounts for test
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
