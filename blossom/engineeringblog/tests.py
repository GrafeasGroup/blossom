from django.test import Client
from django.urls import reverse

from blossom.authentication.models import BlossomUser
from blossom.tests.helpers import create_test_user
from blossom.website.models import Post


def test_properly_empty_blog(client: Client) -> None:
    """Verify that the regular site renders the context appropriately."""
    result = client.get(reverse("blog_index"))
    assert result.status_code == 200
    assert len(result.context["posts"]) == 0


def test_single_post(client: Client, django_user_model: BlossomUser) -> None:
    """Verify that the regular site renders a single post correctly."""
    user = create_test_user(django_user_model)
    post_obj = Post.objects.create(
        title="a", body="b", author=user, engineeringblogpost=True, published=True
    )

    result = client.get(reverse("blog_index"))

    assert result.status_code == 200
    assert result.context["posts"][0] == post_obj
