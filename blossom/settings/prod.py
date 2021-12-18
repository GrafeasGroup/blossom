# noinspection PyUnresolvedReferences
import os

from blossom.settings.base import *  # noqa: F401,F403

ENVIRONMENT = "prod"
MIDDLEWARE = ["bugsnag.django.middleware.BugsnagMiddleware"] + MIDDLEWARE  # noqa: F405

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "bugsnag": {"level": "ERROR", "class": "bugsnag.handlers.BugsnagHandler"},
        "console": {"class": "logging.StreamHandler"},
    },  # noqa: E231
    "loggers": {
        "django": {
            "handlers": ["console", "bugsnag"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "blossom": {
            "handlers": ["console", "bugsnag"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
        },
    },
}
