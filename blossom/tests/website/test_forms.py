import pytest
from django.core.exceptions import ValidationError
from django_hosts.resolvers import reverse

from blossom.tests.helpers import create_test_user, guy, jane
from blossom.website.forms import PostAddForm, AddUserForm


def test_post_form_load(client, django_user_model, setup_site):
    user = create_test_user(django_user_model)
    client.force_login(user)

    result = client.get(reverse("post_create", host="www"))
    assert result.status_code == 200
    for f in result.context['form'].fields:
        assert f in PostAddForm.Meta.fields


def test_adduser_form_load(client, django_user_model, setup_site):
    superuser = create_test_user(django_user_model, superuser=True)
    client.force_login(superuser)

    result = client.get(reverse("user_create", host="www"))
    assert result.status_code == 200
    for f in result.context['form'].fields:
        assert f in AddUserForm.declared_fields


def test_adduser_form_insufficient_privileges(client, django_user_model, setup_site):
    user = create_test_user(django_user_model)
    client.force_login(user)
    result = client.get(reverse("user_create", host="www"))
    assert result.status_code == 302


def test_adduser_form_add_user(client, django_user_model, setup_site):
    superuser = create_test_user(django_user_model, superuser=True)
    client.force_login(superuser)

    data = {
        'username': jane.username,
        'password': jane.password,
        'email': jane.email,
        'is_superuser': "off"  # why the hell is it not True or False‽
    }

    assert django_user_model.objects.filter(username=jane.username).count() == 0
    client.post(reverse("user_create", host="www"), data)
    assert django_user_model.objects.filter(username=jane.username).count() == 1


def test_adduser_form_duplicate_username(client, django_user_model, setup_site):
    superuser = create_test_user(django_user_model, superuser=True)
    client.force_login(superuser)

    data = {
        'username': guy.username,  # same username as our superuser
        'password': guy.password,
        'email': jane.email,  # email that isn't already in the db
        'is_superuser': "off"
    }

    result = client.post(reverse("user_create", host="www"), data)
    assert result.context['form'].errors['username'][0] == "Username already exists"


def test_adduser_form_duplicate_email(client, django_user_model, setup_site):
    superuser = create_test_user(django_user_model, superuser=True)
    client.force_login(superuser)

    data = {
        'username': jane.username,  # username that isn't already in the db
        'password': jane.password,
        'email': guy.email,  # email that is the same as our superuser
        'is_superuser': "off"
    }

    result = client.post(reverse("user_create", host="www"), data)
    assert result.context['form'].errors['email'][0] == "Email already exists"
