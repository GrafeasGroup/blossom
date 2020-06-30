from django.urls import reverse

from blossom.tests.helpers import create_test_user, guy
from website.forms import LoginForm


def test_login_redirect_admin(client, settings):
    resp = client.get(reverse("admin_view"))
    assert resp.get("Location") == "/login/?next=/admin/"


def test_login_redirect_superadmin(client):
    resp = client.get("/superadmin/")
    # this is the built-in django admin panel login page because it's a pain
    # to replace or modify.
    assert resp.get("Location") == "/superadmin/login/?next=/superadmin/"


def test_login(client):
    user = create_test_user()

    response = client.post("/login/", {"email": guy.email, "password": guy.password})

    assert response.status_code == 302
    assert response.wsgi_request.user == user
    assert response.wsgi_request.user.is_authenticated


def test_login_bad_password(client):
    create_test_user()

    response = client.post(
        "/login/", {"email": guy.email, "password": "wrong password"}
    )
    assert response.status_code == 302
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_login_bad_user_info(client):
    response = client.post(
        "/login/", {"email": "a@a.com", "password": "wrong password"}
    )
    assert response.status_code == 302
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_logout(client, setup_site):
    # the setup_site fixture just runs the bootstrap management command
    # so `request()` will work
    user = create_test_user()

    client.force_login(user)

    assert client.request().context.get("user").is_authenticated
    client.get("/logout/")
    assert not client.request().context.get("user").is_authenticated


def test_hosts_redirect(client, setup_site):
    create_test_user(is_grafeas_staff=True)

    response = client.post(
        "/login/?next=/admin/",
        {"email": guy.email, "password": guy.password},
        follow=True,
    )
    assert response.wsgi_request.path == "/admin/"


def test_login_page_request(client, setup_site):
    response = client.get("/login/")
    assert response.status_code == 200
    assert response.context["form"].__class__ == LoginForm
