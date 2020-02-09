import os

import toml
from django.conf import settings


def translation(lang='en_US'):
    with open(os.path.join(settings.BASE_DIR, "strings", f"{lang}.toml"), "r") as f:
        return toml.loads(f.read())
