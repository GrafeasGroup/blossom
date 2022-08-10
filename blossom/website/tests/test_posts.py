from django.test import Client
from django.urls import reverse

from blossom.tests.helpers import create_test_user
from blossom.website.models import Post


def test_post_create(client: Client) -> None:
    """Verify that post creation works as expected."""
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)
    data = {
        "title": "A",
        "body": "B",
        "published": "on",
    }

    assert Post.objects.filter(title="A").count() == 0
    client.post(reverse("post_create"), data)
    assert Post.objects.filter(title="A").count() == 1


def test_post_context(client: Client) -> None:
    """Verify that the appropriate context is returned when viewing a post."""
    user = create_test_user()
    client.force_login(user)

    result = client.get(Post.objects.get(id=1).get_absolute_url())

    assert result.status_code == 200
    # if this is populated, it means that the additional context gathering
    # fired appropriately
    assert result.context["navbar"]


def test_post_edit_context(client: Client) -> None:
    """Verify that the appropriate context is loaded when editing a post."""
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)

    result = client.get(Post.objects.get(id=1).get_absolute_url() + "edit/")
    assert result.status_code == 200
    # if this is populated, it means that the additional context gathering
    # fired appropriately
    assert "enable_trumbowyg" in result.context


def test_post_name(client: Client) -> None:
    """Verify that post names are returned in the proper format."""
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)
    data = {
        "title": "A",
        "body": "B",
        "published": "on",
    }
    client.post(reverse("post_create"), data)
    a_post = Post.objects.get(title="A")
    assert str(a_post) == "A"

    a_post.standalone_section = True
    a_post.header_order = 99
    a_post.save()

    a_post = Post.objects.get(title="A")
    assert str(a_post) == "Section | Header order 99: A"
