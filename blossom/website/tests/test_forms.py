from django.test import Client
from django.urls import reverse

from blossom.authentication.models import BlossomUser
from blossom.tests.helpers import create_test_user, guy, jane
from blossom.website.forms import AddUserForm, PostAddForm


def test_post_form_load(client: Client) -> None:
    """Verify that the correct form loads when creating a post."""
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)

    result = client.get(reverse("post_create"))
    assert result.status_code == 200
    for field in result.context["form"].fields:
        assert field in PostAddForm.Meta.fields


def test_adduser_form_load(client: Client) -> None:
    """Verify that the correct form loads when adding a user."""
    superuser = create_test_user(superuser=True)
    client.force_login(superuser)

    result = client.get(reverse("user_create"))
    assert result.status_code == 200
    for field in result.context["form"].fields:
        assert field in AddUserForm.declared_fields


def test_adduser_form_insufficient_privileges(client: Client) -> None:
    """Verify that a normal user cannot access the adduser form."""
    user = create_test_user()
    client.force_login(user)
    result = client.get(reverse("user_create"))
    assert result.status_code == 302


def test_adduser_form_add_user(client: Client) -> None:
    """Verify that a superuser is able to add users."""
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


def test_adduser_form_duplicate_username(client: Client) -> None:
    """Verify that an error is returned when adding a user with a duplicate username."""
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


def test_adduser_form_duplicate_email(client: Client) -> None:
    """Verify that an error is returned when creating a user with a duplicate email."""
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
