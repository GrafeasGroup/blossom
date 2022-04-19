"""The place where all of our user-facing strings live."""

import os

import toml
from django.conf import settings


def translation(lang: str = "en_US") -> dict:
    """Load and provide the strings file."""
    with open(os.path.join(settings.BASE_DIR, "strings", f"{lang}.toml"), "r") as f:
        return toml.loads(f.read())
