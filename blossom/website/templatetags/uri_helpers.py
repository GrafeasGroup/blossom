from django import template

from blossom.website.models import Post

register = template.Library()


@register.simple_tag
def get_absolute_uri(post: Post) -> str:
    """Return the full URL to a given post."""
    return post.get_absolute_url()
