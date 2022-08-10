"""Set of tests which are used to validate the behavior of the authentication of users."""
from django.test import Client, RequestFactory
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper
from rest_framework import status

from blossom.api.authentication import BlossomApiPermission
from blossom.authentication.models import BlossomUser
from blossom.utils.test_helpers import create_user, setup_user_client

USER_CREATION_DATA = {"username": "Narf"}


def test_creation_without_authentication(client: Client) -> None:
    """Test whether creation without logging in nor providing an API key is forbidden."""
    assert len(BlossomUser.objects.all()) == 4
    result = client.post(reverse("volunteer-list"), USER_CREATION_DATA)
    assert result.status_code == status.HTTP_403_FORBIDDEN
    assert len(BlossomUser.objects.all()) == 4


def test_creation_without_api_key(client: Client) -> None:
    """Test whether creation without sending the API key whilst logged in is forbidden."""
    client, headers, _ = setup_user_client(
        client, is_staff=False, is_grafeas_staff=False
    )
    result = client.get(reverse("volunteer-list"), USER_CREATION_DATA)
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_without_login(client: Client) -> None:
    """Test whether creation without logging in to an allowed user is forbidden."""
    client, headers, _ = setup_user_client(client, login=False)
    result = client.post(reverse("volunteer-list"), USER_CREATION_DATA, **headers)
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_wrong_header_format(client: Client) -> None:
    """Test whether creation without proper header format is forbidden."""
    client, headers, _ = setup_user_client(
        client, is_staff=False, is_grafeas_staff=False
    )
    # Deform the header, so that it looks like {Authorization: mykey} instead of
    # {Authorization: Api-Key mykey}.
    headers["HTTP_AUTHORIZATION"] = headers.get("HTTP_AUTHORIZATION").split()[1]
    result = client.get(reverse("volunteer-list"), USER_CREATION_DATA, **headers)
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_with_normal_user(client: Client) -> None:
    """Test whether creation is not allowed to a user which is not a staff member."""
    client, headers, _ = setup_user_client(
        client, is_grafeas_staff=False, is_staff=False
    )
    result = client.post(reverse("volunteer-list"), USER_CREATION_DATA)
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_allowed(client: Client) -> None:
    """
    Test whether creation is allowed when properly authenticated.

    This proper authenticated is when the client is logged in as a staff member,
    and the corresponding API Key is provided.
    """
    client, headers, _ = setup_user_client(client)
    previous_user_count = BlossomUser.objects.count()
    result = client.post(reverse("volunteer-list"), USER_CREATION_DATA, **headers)
    assert result.json().get("username") == "Narf"
    assert result.status_code == status.HTTP_201_CREATED
    assert BlossomUser.objects.count() == previous_user_count + 1


class TestPermissionsCheck:
    """Tests designed to validate the behavior of the permission checker."""

    def test_permissions_normal_user(self, rf: RequestFactory) -> None:
        """Test whether the API does not allow normal users access."""
        user = create_user(is_staff=False, is_grafeas_staff=False)
        request = rf.get("/")
        request.user = user
        assert not BlossomApiPermission().has_permission(request, None)

    def test_permissions_super_user(self, rf: RequestFactory) -> None:
        """Test whether the API does allow superusers without API key access."""
        user = create_user()
        request = rf.get("/")
        request.user = user
        assert BlossomApiPermission().has_permission(request, None)

    def test_permissions_grafeas_staff_no_api_key(self, rf: RequestFactory) -> None:
        """Test whether the API does not allow access to Grafeas staff without API key."""
        # this should fail because they don't have an api key
        user = create_user(is_staff=False)
        request = rf.get("/")
        request.user = user
        assert not BlossomApiPermission().has_permission(request, None)

    def test_permissions_grafeas_staff_api_key(
        self, client: Client, rf: RequestFactory
    ) -> None:
        """Test whether the API allows access to Grafeas staff members."""
        client, headers, _ = setup_user_client(client)
        # four system accounts first
        user = BlossomUser.objects.get(id=5)
        request = rf.get("/")
        request.user = user
        request.META.update(headers)
        assert BlossomApiPermission().has_permission(request, None)

    def test_permissions_override_api_auth(
        self, rf: RequestFactory, settings: SettingsWrapper
    ) -> None:
        """Test whether the API does allow superusers without API key access."""
        # first, verify that access is denied
        user = create_user(is_staff=False, is_grafeas_staff=False)
        request = rf.get("/")
        request.user = user
        assert not BlossomApiPermission().has_permission(request, None)

        # now make sure it works with the flag toggled on
        settings.OVERRIDE_API_AUTH = True
        request = rf.get("/")
        request.user = user
        assert BlossomApiPermission().has_permission(request, None)
