from django.urls import reverse

from blossom.tests.helpers import create_test_user
from website.models import Post


def test_post_create(client):
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


def test_post_context(client, setup_site):
    user = create_test_user()
    client.force_login(user)

    result = client.get(Post.objects.get(id=1).get_absolute_url())

    assert result.status_code == 200
    # if this is populated, it means that the additional context gathering
    # fired appropriately
    assert result.context["navbar"]


def test_post_edit_context(client, setup_site):
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)

    result = client.get(Post.objects.get(id=1).get_absolute_url() + "edit/")
    assert result.status_code == 200
    # if this is populated, it means that the additional context gathering
    # fired appropriately
    assert "enable_trumbowyg" in result.context


def test_post_name(client):
    user = create_test_user(is_grafeas_staff=True)
    client.force_login(user)
    data = {
        "title": "A",
        "body": "B",
        "published": "on",
    }
    client.post(reverse("post_create"), data)
    a = Post.objects.get(title="A")
    assert str(a) == "A"

    a.standalone_section = True
    a.header_order = 99
    a.save()

    a = Post.objects.get(title="A")
    assert str(a) == "Section | Header order 99: A"
