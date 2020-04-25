"""Set of tests which are used to validate the behavior of the authentication of users."""
from django.test import Client, RequestFactory
from django_hosts.resolvers import reverse
from rest_framework import status

from api.authentication import BlossomApiPermission
from api.tests.helpers import create_user, setup_user_client
from authentication.models import BlossomUser

USER_CREATION_DATA = {"username": "Narf"}


def test_creation_without_authentication(client: Client) -> None:
    """Test whether creation without logging in nor providing an API key is forbidden."""
    assert len(BlossomUser.objects.all()) == 0
    result = client.post(
        reverse("volunteer-list", host="api"), USER_CREATION_DATA, HTTP_HOST="api"
    )
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_without_api_key(client: Client) -> None:
    """Test whether creation without sending the API key whilst logged in is forbidden."""
    client, headers, _ = setup_user_client(client)
    result = client.get(
        reverse("volunteer-list", host="api"), USER_CREATION_DATA, HTTP_HOST="api"
    )
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_without_login(client: Client) -> None:
    """Test whether creation without logging in to an allowed user is forbidden."""
    client, headers, _ = setup_user_client(client, login=False)
    result = client.post(
        reverse("volunteer-list", host="api"),
        USER_CREATION_DATA,
        HTTP_HOST="api",
        **headers
    )
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_wrong_header_format(client: Client) -> None:
    """Test whether creation without proper header format is forbidden."""
    client, headers, _ = setup_user_client(client)
    # Deform the header, so that it looks like {Authorization: mykey} instead of
    # {Authorization: Api-Key mykey}.
    headers["HTTP_AUTHORIZATION"] = headers.get("HTTP_AUTHORIZATION").split()[1]
    result = client.get(
        reverse("volunteer-list", host="api"),
        USER_CREATION_DATA,
        HTTP_HOST="api",
        **headers
    )
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_with_normal_user(client: Client) -> None:
    """Test whether creation is not allowed to a user which is not a staff member."""
    client, headers, _ = setup_user_client(
        client, is_grafeas_staff=False, is_staff=False
    )
    result = client.post(
        reverse("volunteer-list", host="api"), USER_CREATION_DATA, HTTP_HOST="api"
    )
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_creation_allowed(client: Client) -> None:
    """
    Test whether creation is allowed when properly authenticated.

    This proper authenticated is when the client is logged in as a staff member,
    and the corresponding API Key is provided.
    """
    client, headers, _ = setup_user_client(client)
    result = client.post(
        reverse("volunteer-list", host="api"),
        USER_CREATION_DATA,
        HTTP_HOST="api",
        **headers
    )
    assert result.json().get("username") == "Narf"
    assert result.status_code == status.HTTP_201_CREATED
    assert len(BlossomUser.objects.all()) == 2


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
        user = BlossomUser.objects.get(id=1)
        request = rf.get("/")
        request.user = user
        request.META.update(headers)
        assert BlossomApiPermission().has_permission(request, None)
