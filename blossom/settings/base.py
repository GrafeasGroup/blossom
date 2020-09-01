"""
Django settings for blossom project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import logging
import os

import dotenv
from django.urls import reverse_lazy

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
default_secret_key = "v7-fg)i9rb+&kx#c-@m2=6qdw)o*2x787!fl8-xbv5h&%gr8xx"
SECRET_KEY = os.environ.get("BLOSSOM_SECRET_KEY", default_secret_key)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# force cross-domain cookies so that wiki login can use the regular login page
ALLOWED_HOSTS = [".grafeas.org/", "grafeas.org/"]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static_dev")]

LOGIN_URL = reverse_lazy("login")
LOGOUT_URL = reverse_lazy("logout")

# disallow creating accounts through the wiki
WIKI_ACCOUNT_HANDLING = False
# disallow anonymous viewing
WIKI_ANONYMOUS = False

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # additional functionality
    "widget_tweaks",
    # wiki
    "django.contrib.sites.apps.SitesConfig",
    "django.contrib.humanize.apps.HumanizeConfig",
    "django_nyt.apps.DjangoNytConfig",
    "mptt",
    "sekizai",
    "sorl.thumbnail",
    "wiki.apps.WikiConfig",
    "wiki.plugins.attachments.apps.AttachmentsConfig",
    # todo: this is super broken for some reason
    # 'wiki.plugins.notifications.apps.NotificationsConfig',
    "wiki.plugins.images.apps.ImagesConfig",
    "wiki.plugins.macros.apps.MacrosConfig",
    # blossom internal apps
    "blossom",
    "api",
    "authentication",
    "engineeringblog",
    "payments",
    "ocr",
    "website",
    # API
    "rest_framework",
    "rest_framework_api_key",
    "drf_yasg",
    # Social authentication
    "social_django",
]

AUTH_USER_MODEL = "authentication.BlossomUser"

MIDDLEWARE = [
    "bugsnag.django.middleware.BugsnagMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # One month
ROOT_URLCONF = "blossom.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
            os.path.join(BASE_DIR, "templates", "wiki"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
            ],
        },
    },
]

WSGI_APPLICATION = "blossom.wsgi.application"

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

default_db_password = "Pink fluffy unicorns dancing on rainbows"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "blossom",
        "USER": "blossom_app",
        "PASSWORD": os.getenv("BLOSSOM_DB_PASSWORD", default_db_password),
        "HOST": "localhost",
        "PORT": "",
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
            "level": os.getenv("DJANGO_LOG_LEVEL", "DEBUG"),
        },
    },
}

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_PERMISSION_CLASSES": ("api.authentication.BlossomApiPermission",),
}
API_KEY_CUSTOM_HEADER = "HTTP_X_API_KEY"

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "authentication.backends.EmailBackend",
    "blossom.social_auth.reddit.RedditOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

SITE_ID = 1

OVERRIDE_API_AUTH = False

# number of hours to allow a post to stay up
ARCHIVIST_DELAY_TIME = 18
# number of hours to allow a completed post to stay up
ARCHIVIST_COMPLETED_DELAY_TIME = 0.5

# Global flag; if this is set to False, all slack calls will fail silently
ENABLE_SLACK = True

GITHUB_SPONSORS_SECRET_KEY = os.environ.get("GITHUB_SPONSORS_SECRET_KEY", "")

# Global flag; if this is set to False, all calls to ocr.space will fail silently
ENABLE_OCR = True

# Only enable if there are connection problems with all three primary endpoints
OCR_ENABLE_BACKUP_ENDPOINT = os.getenv("OCR_ENABLE_BACKUP_ENDPOINT", False)
# "helloworld" is a valid API key, however use it sparingly
OCR_API_KEY = os.getenv("OCR_API_KEY", "helloworld")

OCR_API_URLS = [
    "https://apipro1.ocr.space/parse/image",  # USA
    "https://apipro2.ocr.space/parse/image",  # Europe
    "https://apipro3.ocr.space/parse/image",  # Asia
]

if OCR_ENABLE_BACKUP_ENDPOINT:
    # unofficial backup endpoint. May or may not be up at any given time.
    OCR_API_URLS += ["https://apix.ocr.space/parse/image"]

OCR_NOOP_MODE = bool(os.getenv("OCR_NOOP_MODE", ""))
OCR_DEBUG_MODE = bool(os.getenv("OCR_DEBUG_MODE", ""))

ENABLE_REDDIT = False

IMAGE_DOMAINS = [
    "imgur.com",
    "i.imgur.com",
    "m.imgur.com",
    "i.reddit.com",
    "i.redd.it",
    "puu.sh",
    "i.redditmedia.com",
]

###############################################
# simple validation -- add new keys above this
###############################################


def settings_err(msg: str) -> None:
    """Print a simple formatted warning."""
    logger.warning("*" * 39)
    logger.warning(msg)
    logger.warning("*" * 39)


if SECRET_KEY == default_secret_key:
    settings_err("Using default secret key!")

if DATABASES["default"].get("PASSWORD") == default_db_password:
    settings_err("Using default database password!")

if OCR_API_KEY == "helloworld":
    settings_err("Using default OCR API key, not ours!")
