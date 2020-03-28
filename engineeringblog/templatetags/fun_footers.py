import random

from django import template

from blossom.strings import translation

register = template.Library()
i18n = translation()


@register.simple_tag
def generate_engineering_footer():
    return random.choice(i18n['footer']['messages'])
