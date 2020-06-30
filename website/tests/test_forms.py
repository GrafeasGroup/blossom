from django.urls import reverse

from authentication.models import BlossomUser
from blossom.tests.helpers import create_test_user, guy, jane
from website.forms import AddUserForm, PostAddForm


def test_post_form_load(client, setup_site):
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)

    result = client.get(reverse("post_create"))
    assert result.status_code == 200
    for f in result.context["form"].fields:
        assert f in PostAddForm.Meta.fields


def test_adduser_form_load(client, setup_site):
    superuser = create_test_user(superuser=True)
    client.force_login(superuser)

    result = client.get(reverse("user_create"))
    assert result.status_code == 200
    for f in result.context["form"].fields:
        assert f in AddUserForm.declared_fields


def test_adduser_form_insufficient_privileges(client, setup_site):
    user = create_test_user()
    client.force_login(user)
    result = client.get(reverse("user_create"))
    assert result.status_code == 302


def test_adduser_form_add_user(client, setup_site):
    superuser = create_test_user(superuser=True)
    client.force_login(superuser)

    data = {
        "username": jane.username,
        "password": jane.password,
        "email": jane.email,
        "is_superuser": "off",  # why the hell is it not True or False‽
    }

    assert BlossomUser.objects.filter(username=jane.username).count() == 0
    client.post(reverse("user_create"), data)
    assert BlossomUser.objects.filter(username=jane.username).count() == 1


def test_adduser_form_duplicate_username(client, setup_site):
    superuser = create_test_user(superuser=True)
    client.force_login(superuser)

    data = {
        "username": guy.username,  # same username as our superuser
        "password": guy.password,
        "email": jane.email,  # email that isn't already in the db
        "is_superuser": "off",
    }

    result = client.post(reverse("user_create"), data)
    assert result.context["form"].errors["username"][0] == "Username already exists"


def test_adduser_form_duplicate_email(client, setup_site):
    superuser = create_test_user(superuser=True)
    client.force_login(superuser)

    data = {
        "username": jane.username,  # username that isn't already in the db
        "password": jane.password,
        "email": guy.email,  # email that is the same as our superuser
        "is_superuser": "off",
    }

    result = client.post(reverse("user_create"), data)
    assert result.context["form"].errors["email"][0] == "Email already exists"
