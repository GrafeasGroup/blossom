import json

from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.tests.helpers import (
    create_test_user, create_volunteer, create_staff_volunteer_with_keys
)


def test_edit_volunteer(client):
    client, headers = create_staff_volunteer_with_keys(client)
    data = {'username': 'naaaarf'}
    assert BlossomUser.objects.get(id=1).username == "janeeyre"
    client.put(
        reverse('volunteer-detail', args=[1], host='api'),
        json.dumps(data),
        HTTP_HOST='api',
        content_type='application/json',
        **headers,
    )
    assert BlossomUser.objects.get(id=1).username == "naaaarf"
