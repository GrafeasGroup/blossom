import pytest

# from django.urls import reverse
from django_hosts.resolvers import reverse
from blossom.api.models import Volunteer, APIKey
from blossom.tests.helpers import create_test_user, create_volunteer


def test_volunteer_creation_without_credentials(client):
    data = {
        'username': 'Narf'
    }
    assert len(Volunteer.objects.all()) == 0
    result = client.post(reverse('volunteer-list', host='api'), data, HTTP_HOST='api')
    assert result.status_code == 403


def test_volunteer_creation_with_normal_user(client, django_user_model):
    user = create_test_user(django_user_model)
    client.force_login(user)

    data = {
        'username': 'Narf'
    }

    assert len(Volunteer.objects.all()) == 0
    result = client.post(reverse('volunteer-list', host='api'), data, HTTP_HOST='api')
    assert result.status_code == 403


def test_volunteer_creation_with_admin_user(client, django_user_model):
    user = create_test_user(django_user_model, superuser=True)
    client.force_login(user)

    data = {
        'username': 'Narf'
    }

    assert len(Volunteer.objects.all()) == 0
    client.post(reverse('volunteer-list', host='api'), data, HTTP_HOST='api')
    assert len(Volunteer.objects.all()) == 1


def test_volunteer_creation_with_non_admin_api_key(client):
    v, headers = create_volunteer(with_api_key=True)

    data = {
        'username': 'Narf'
    }

    assert len(Volunteer.objects.filter(username="Narf")) == 0
    result = client.post(
        reverse('volunteer-list', host='api'), data, **headers, HTTP_HOST='api'
    )
    assert result.json() == {'detail': 'Authentication credentials were not provided.'}


def test_volunteer_creation_with_admin_api_key(client, django_user_model):
    user = create_test_user(django_user_model)
    v, headers = create_volunteer(with_api_key=True)
    v.staff_account = user
    v.save()
    client.force_login(user)

    data = {
        'username': 'Narf'
    }

    assert len(Volunteer.objects.filter(username="Narf")) == 0
    result = client.post(
        reverse('volunteer-list', host='api'), data, **headers, HTTP_HOST='api'
    )
    assert result.json() == {'success': 'Volunteer created with username `Narf`'}
