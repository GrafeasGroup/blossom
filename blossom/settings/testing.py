# noinspection PyUnresolvedReferences
from blossom.settings.base import *

ENVIRONMENT = "testing"
DEBUG = True
ALLOWED_HOSTS = ["*"]
SESSION_COOKIE_DOMAIN = "grafeas.localhost"
PARENT_HOST = "grafeas.localhost:8000"
# Cave Johnson, Portal 2.
SECRET_KEY = (
    "There's a thousand tests performed every day here in our enrichment spheres."
    " I can't personally oversee every one of them, so these pre-recorded messages'll"
    " cover any questions you might have, and respond to any incidents that may"
    " occur in the course of your science adventure."
)

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache",}}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler",},},
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
