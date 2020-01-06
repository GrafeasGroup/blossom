from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.api.authentication import BlossomApiPermission
from blossom.tests.helpers import (
    create_test_user,
    create_volunteer,
    create_staff_volunteer_with_keys,
)


def test_volunteer_creation_without_credentials(client):
    data = {"username": "Narf"}
    assert len(BlossomUser.objects.all()) == 0
    result = client.post(reverse("volunteer-list", host="api"), data, HTTP_HOST="api")
    assert result.status_code == 403


def test_volunteer_creation_with_normal_user(client):
    user = create_test_user()
    client.force_login(user)

    data = {"username": "Narf"}

    assert len(BlossomUser.objects.all()) == 1  # the one we just created
    result = client.post(reverse("volunteer-list", host="api"), data, HTTP_HOST="api")
    assert result.status_code == 403


def test_volunteer_creation_with_admin_user(client):
    client, headers = create_staff_volunteer_with_keys(client)

    data = {"username": "Narf"}

    assert len(BlossomUser.objects.all()) == 1
    client.post(reverse("volunteer-list", host="api"), data, HTTP_HOST="api", **headers)
    assert len(BlossomUser.objects.all()) == 2


def test_volunteer_creation_with_non_admin_api_key(client):
    v, headers = create_volunteer(with_api_key=True)

    data = {"username": "Narf"}

    assert len(BlossomUser.objects.filter(username="Narf")) == 0
    result = client.post(
        reverse("volunteer-list", host="api"), data, **headers, HTTP_HOST="api"
    )
    assert result.json() == {"detail": "Authentication credentials were not provided."}


def test_volunteer_creation_with_admin_api_key(client):
    client, headers = create_staff_volunteer_with_keys(client)
    data = {"username": "Narf"}

    assert len(BlossomUser.objects.filter(username="Narf")) == 0
    result = client.post(
        reverse("volunteer-list", host="api"), data, **headers, HTTP_HOST="api"
    )
    assert result.json().get("message") == "Volunteer created with username `Narf`"


class TestPermissionsCheck:
    def test_permissions_1(self, rf):
        user = create_test_user()
        request = rf.get("/")
        request.user = user
        assert not BlossomApiPermission().has_permission(request, None)

    def test_permissions_2(self, rf):
        user = create_test_user(superuser=True)
        request = rf.get("/")
        request.user = user
        assert BlossomApiPermission().has_permission(request, None)

    def test_permissions_3(self, rf):
        # this should fail because they don't have an api key
        user = create_test_user(is_grafeas_staff=True)
        request = rf.get("/")
        request.user = user
        assert not BlossomApiPermission().has_permission(request, None)

    def test_permissions_4(self, client, rf):
        client, headers = create_staff_volunteer_with_keys(client)
        user = BlossomUser.objects.get(id=1)
        request = rf.get("/")
        request.user = user
        request.META.update(headers)
        assert BlossomApiPermission().has_permission(request, None)
