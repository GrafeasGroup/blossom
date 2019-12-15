from django_hosts.resolvers import reverse

from blossom.website.models import Post
from blossom.tests.helpers import create_test_user


def test_properly_empty_blog(client, setup_site):
    result = client.get(
        reverse('blog_index', host='engineeringblog'), HTTP_HOST='engineering'
    )
    assert result.status_code == 200
    assert len(result.context['posts']) == 0


def test_single_post(client, setup_site, django_user_model):
    user = create_test_user(django_user_model)
    post_obj = Post.objects.create(
        title='a',
        body='b',
        author=user,
        engineeringblogpost=True,
        published=True
    )

    result = client.get(
        reverse('blog_index', host='engineeringblog'), HTTP_HOST='engineering'
    )

    assert result.status_code == 200
    assert result.context['posts'][0] == post_obj
