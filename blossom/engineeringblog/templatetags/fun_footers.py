import random

from django import template

from blossom.strings import translation

register = template.Library()
i18n = translation()


@register.simple_tag
def generate_engineering_footer() -> str:
    """Return a random message to display on the site."""
    return random.choice(i18n["footer"]["messages"])
