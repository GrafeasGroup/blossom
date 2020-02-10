"""
Django settings for blossom project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import logging

import dotenv
from django_hosts.resolvers import reverse_lazy

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
default_secret_key = "v7-fg)i9rb+&kx#c-@m2=6qdw)o*2x787!fl8-xbv5h&%gr8xx"
SECRET_KEY = os.environ.get(
    "BLOSSOM_SECRET_KEY", default_secret_key
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# force cross-domain cookies so that wiki login can use the regular login page
ALLOWED_HOSTS = [".grafeas.org/", "grafeas.org/"]
SESSION_COOKIE_DOMAIN = "grafeas.org"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static_dev")]

LOGIN_URL = reverse_lazy("login", host="www")
LOGOUT_URL = reverse_lazy("logout", host="www")

# for subdomain routing
ROOT_HOSTCONF = "blossom.hosts"
DEFAULT_HOST = "www"
PARENT_HOST = "grafeas.org"

# wiki
WIKI_ACCOUNT_HANDLING = False
# ideally, we would handle this with the following line:
# WIKI_ANONYMOUS = False
# but if we do, then the forced login redirects with a `next` parameter of '/',
# which of course sends us back to the regular site instead of the proper
# subdomain. Perhaps something to look into in the future.
# todo: fix anonymous handling

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_hosts",
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
    "blossom",
    "rest_framework",
    "rest_framework_api_key",
    "drf_yasg",
    "social_django",
]

AUTH_USER_MODEL = "blossom.BlossomUser"

MIDDLEWARE = [
    "bugsnag.django.middleware.BugsnagMiddleware",
    "django_hosts.middleware.HostsRequestMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "blossom.wiki.middleware.wiki_media_url_rewrite",
    "django_hosts.middleware.HostsResponseMiddleware",
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
        "PASSWORD": os.getenv(
            "BLOSSOM_DB_PASSWORD", default_db_password
        ),
        "HOST": "localhost",
        "PORT": "",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_PERMISSION_CLASSES": ("blossom.api.authentication.BlossomApiPermission",),
}
API_KEY_CUSTOM_HEADER = "HTTP_X_API_KEY"

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]

AUTHENTICATION_BACKENDS = [
    "blossom.authentication.backends.EmailBackend",
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
# how long to allow a completed post to stay up
ARCHIVIST_COMPLETED_DELAY_TIME = 0.5


##############################################
# simple validation -- add new keys above this
##############################################

def settings_err(msg):
    logger.warning("*" * 39)
    logger.warning(msg)
    logger.warning("*" * 39)

if SECRET_KEY == default_secret_key:
    settings_err("Using default secret key!")

if DATABASES['default']['PASSWORD'] == default_db_password:
    settings_err("Using default database password!")
