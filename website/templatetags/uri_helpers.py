from django import template

register = template.Library()


@register.simple_tag
def get_absolute_uri(post, host):
    return post.get_absolute_url()
