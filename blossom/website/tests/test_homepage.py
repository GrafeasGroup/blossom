from django.test import Client

from blossom.authentication.models import BlossomUser
from blossom.tests.helpers import create_test_user
from blossom.website.models import Post


def test_homepage_setup(client: Client) -> None:
    """Verify that the homepage works."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_homepage_navbar_contents_while_not_logged_in(client: Client) -> None:
    """Verify that the navbar behaves appropriately when not logged in."""
    resp = client.get("/")
    assert len(resp.context["navbar"]) == 2
    assert b'href="/">News</a>' in resp.content
    assert b"https://github.com/GrafeasGroup/" in resp.content
    assert b'id="adminView"' not in resp.content
    assert b'id="logoutButton"' not in resp.content


def test_homepage_navbar_contents_logged_in(
    client: Client, django_user_model: BlossomUser
) -> None:
    """Verify that the navbar behaves appropriately when logged in as non-staff."""
    user = create_test_user(django_user_model)
    client.force_login(user)

    resp = client.get("/")
    assert len(resp.context["navbar"]) == 2
    assert b'id="adminView"' not in resp.content  # not staff
    assert b'id="logoutButton"' in resp.content


def test_homepage_navbar_contents_logged_in_admin(
    client: Client, django_user_model: BlossomUser
) -> None:
    """Verify that the navbar behaves appropriately when logged in as staff."""
    user = create_test_user(django_user_model, is_grafeas_staff=True)
    client.force_login(user)

    resp = client.get("/")
    assert b'id="adminView"' in resp.content


def test_homepage_post_view(client: Client, django_user_model: BlossomUser) -> None:
    """Verify that the homepage works appropriately."""
    user = create_test_user(django_user_model)
    resp = client.get("/")
    assert len(resp.context["posts"]) == 0
    p1 = Post.objects.create(
        title="TestPost1", body="testpost1", author=user, published=True
    )

    resp = client.get("/")
    assert len(resp.context["posts"]) == 1
    assert p1 in resp.context["posts"]

    p2 = Post.objects.create(
        title="TestPost2", body="testpost2", author=user, published=True
    )

    resp = client.get("/")
    assert len(resp.context["posts"]) == 2
    assert p1 in resp.context["posts"]
    assert p2 in resp.context["posts"]
