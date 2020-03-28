from django_hosts import reverse

from api.helpers import VolunteerMixin
from blossom.tests.helpers import create_staff_volunteer_with_keys
from blossom.tests.helpers import create_volunteer


def test_ping(client):
    result = client.get(
        reverse("ping", host="api"), HTTP_HOST="api", content_type="application/json",
    )
    assert result.json() == {"ping?!": "PONG"}


def test_summary(client):
    client, headers = create_staff_volunteer_with_keys(client)

    result = client.get(
        reverse("summary", host="api"),
        HTTP_HOST="api",
        content_type="application/json",
        **headers,
    )
    assert len(result.json().keys()) == 3
    assert result.status_code == 200


def test_volunteer_get():
    v = create_volunteer()
    assert VolunteerMixin().get_volunteer(username=v.username) == v
