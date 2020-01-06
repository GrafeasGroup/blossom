import random
import os

from django import template
from django.conf import settings
import toml

register = template.Library()

with open(os.path.join(settings.BASE_DIR, "strings", "footers.toml"), "r") as f:
    footers = toml.loads(f.read())

@register.simple_tag
def generate_engineering_footer():
    return random.choice(footers['data']['messages'])
