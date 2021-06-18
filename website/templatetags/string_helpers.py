from django import template
from django.template.defaultfilters import safe, stringfilter

register = template.Library()


@register.filter
@stringfilter
def trim_label(string: str, count: int) -> str:
    """Take the label_tag and remove `count` characters."""
    beginning = string.index(">") + 1
    end = string.rindex("<")
    content = string[beginning:end][:-count]

    return safe(string[:beginning] + content + string[end:])
