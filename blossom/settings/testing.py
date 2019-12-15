# noinspection PyUnresolvedReferences
from blossom.settings.base import *

ENVIRONMENT = 'testing'
DEBUG = True
ALLOWED_HOSTS = ['*']
SESSION_COOKIE_DOMAIN = "grafeas.localhost"
PARENT_HOST = 'grafeas.localhost:8000'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'blossom': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO')
        }
    },
}
