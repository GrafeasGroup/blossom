import os

from blossom.settings.base import *  # noqa: F403

ENVIRONMENT = "testing"
DEBUG = True
ALLOWED_HOSTS = ["*"]
# Cave Johnson, Portal 2.
SECRET_KEY = (
    "There's a thousand tests performed every day here in our enrichment spheres."
    " I can't personally oversee every one of them, so these pre-recorded messages'll"
    " cover any questions you might have, and respond to any incidents that may"
    " occur in the course of your science adventure."
)

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache",}  # noqa: E231
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),  # noqa: F405
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler",},},  # noqa: E231
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "blossom": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    },
}

ENABLE_SLACK = False
ENABLE_OCR = False
ENABLE_REDDIT = False
