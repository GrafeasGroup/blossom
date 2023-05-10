from django.test import Client
from django.urls import reverse

from blossom.tests.helpers import create_test_user, guy
from blossom.website.forms import LoginForm


def test_login_redirect_admin(client: Client) -> None:
    """Assert that the staff admin page gets redirected to the login page."""
    resp = client.get(reverse("admin_view"))
    assert resp.get("Location") == "/login/?next=/admin/"


def test_login_redirect_superadmin(client: Client) -> None:
    """Assert that the superadmin page gets redirected to the django admin sign-in."""
    resp = client.get("/superadmin/")
    # this is the built-in django admin panel login page because it's a pain
    # to replace or modify.
    assert resp.get("Location") == "/superadmin/login/?next=/superadmin/"


def test_login(client: Client) -> None:
    """Assert that logging in works as expected."""
    user = create_test_user()

    response = client.post("/login/", {"email": guy.email, "password": guy.password})

    assert response.status_code == 302
    assert response.wsgi_request.user == user
    assert response.wsgi_request.user.is_authenticated


def test_login_bad_password(client: Client) -> None:
    """Assert that logging in with an incorrect password does not work."""
    create_test_user()

    response = client.post(
        "/login/", {"email": guy.email, "password": "wrong password"}, follow=True
    )
    assert response.status_code == 200
    assert len(list(response.context["messages"])) == 1
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_login_bad_user_info(client: Client) -> None:
    """Assert that attempting a login with the wrong username and password fails."""
    response = client.post(
        "/login/", {"email": "a@a.com", "password": "wrong password"}, follow=True
    )
    assert response.status_code == 200

    messages = [m.message for m in response.context["messages"]]

    assert len(messages) == 1
    assert "didn't look right" in messages[0]
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_login_garbage_info(client: Client) -> None:
    """Assert that attempting a login with garbage fails cleanly."""
    response = client.post("/login/", {"AAAAAA": "BBBBBBBB", "CCCCCCC": "DDDDDDD"}, follow=True)
    assert response.status_code == 200

    messages = [m.message for m in response.context["messages"]]

    assert len(messages) == 1
    assert "something went wrong" in messages[0]
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_logout(client: Client) -> None:
    """Assert that logging out successfully logs the user out."""
    user = create_test_user()

    client.force_login(user)

    assert client.request().context.get("user").is_authenticated
    client.get("/logout/")
    assert not client.request().context.get("user").is_authenticated


def test_after_login_redirect(client: Client) -> None:
    """Verify that users are redirected to the page they were attempting to reach."""
    create_test_user(is_grafeas_staff=True)

    response = client.post(
        "/login/?next=/admin/",
        {"email": guy.email, "password": guy.password},
        follow=True,
    )
    assert response.wsgi_request.path == "/admin/"


def test_login_page_request(client: Client) -> None:
    """Verify that the LoginForm is served when visiting the login page."""
    response = client.get("/login/")
    assert response.status_code == 200
    assert response.context["form"].__class__ == LoginForm
