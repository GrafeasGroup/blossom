from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.tests.helpers import create_test_user, create_volunteer


def test_volunteer_creation_without_credentials(client):
    data = {
        'username': 'Narf'
    }
    assert len(BlossomUser.objects.all()) == 0
    result = client.post(reverse('volunteer-list', host='api'), data, HTTP_HOST='api')
    assert result.status_code == 403


def test_volunteer_creation_with_normal_user(client):
    user = create_test_user()
    client.force_login(user)

    data = {
        'username': 'Narf'
    }

    assert len(BlossomUser.objects.all()) == 1  # the one we just created
    result = client.post(reverse('volunteer-list', host='api'), data, HTTP_HOST='api')
    assert result.status_code == 403


def test_volunteer_creation_with_admin_user(client):
    user = create_test_user(superuser=True)
    client.force_login(user)

    data = {
        'username': 'Narf'
    }

    assert len(BlossomUser.objects.all()) == 1
    client.post(reverse('volunteer-list', host='api'), data, HTTP_HOST='api')
    assert len(BlossomUser.objects.all()) == 2


def test_volunteer_creation_with_non_admin_api_key(client):
    v, headers = create_volunteer(with_api_key=True)

    data = {
        'username': 'Narf'
    }

    assert len(BlossomUser.objects.filter(username="Narf")) == 0
    result = client.post(
        reverse('volunteer-list', host='api'), data, **headers, HTTP_HOST='api'
    )
    assert result.json() == {'detail': 'Authentication credentials were not provided.'}


def test_volunteer_creation_with_admin_api_key(client):
    v, headers = create_volunteer(with_api_key=True)
    client.force_login(v)

    data = {
        'username': 'Narf'
    }

    assert len(BlossomUser.objects.filter(username="Narf")) == 0
    result = client.post(
        reverse('volunteer-list', host='api'), data, **headers, HTTP_HOST='api'
    )
    assert result.json() == {'success': 'Volunteer created with username `Narf`'}
