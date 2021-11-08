![Image of Blossom, from 1998's Powerpuff Girls](https://i.imgur.com/Rao8pA9.png)

<h1 align="center">blossom</h1>

<p align="center">
<a href="https://github.com/grafeasgroup/blossom/actions"><img alt="Actions Status" src="https://github.com/grafeasgroup/blossom/workflows/Django%20CI/badge.svg"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href='https://coveralls.io/github/GrafeasGroup/blossom?branch=master'><img src='https://coveralls.io/repos/github/GrafeasGroup/blossom/badge.svg?branch=master&amp;t=X9mgMK' alt='Coverage Status' /></a>
</p>

The website. The app. The everything.

A Django app that serves our website, payment portal for donations, engineering blog, and API. It can be found at https://grafeas.org.

## Local development

> For a quick and dirty method of testing blossom locally, run `docker-compose up -d` and point your browser to <http://localhost:8080/>

Create a file at the top level called `local_settings.py`. Populate it with the following:

```python
# noinspection PyUnresolvedReferences
from blossom.settings.local import *
import better_exceptions
import os
# trust me, this will make your life better.
better_exceptions.MAX_LENGTH = None

# Use this file when developing locally -- it has some helpful additions which
# change how the server runs.
DEBUG = True
ENABLE_SLACK = False

ALLOWED_HOSTS = ['*']
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# ideally this should be postgres, but developing against sqlite3 will work.
# Just be aware of potential issues where sqlite3 and postgres do not play well
# together -- namely, django migrations for sqlite3 will allow a field creation
# and field alter call in the same transaction. Postgres... will not.
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
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG')
        }
    },
}

OVERRIDE_API_AUTH = True
ENABLE_OCR = False
MIDDLEWARE = [i for i in MIDDLEWARE if "bugsnag" not in i]
MIDDLEWARE = ["blossom.middleware.BetterExceptionsMiddleware"] + MIDDLEWARE
```
This file will be ignored by git, so make any changes you need to while developing.

## Pre-commits

Blossom uses `pre-commit` to help us keep everything clean. After you check out the repo and run `poetry install`, run `pre-commit install` to configure the system. The first time that you run `git commit`, it will create a small venv specifically for checking commits based on our toolset. All of these are installed as part of the regular project so that you can run them as you go -- don't get taken by surprise when you go to commit! The toolchain as written invokes the following tools:

- seed-isort-config
  - This sets .isort.cfg with all of the third-party modules that are in use.
- isort
  - Searches Python files for imports that are in the wrong order, then offers you the option of fixing them.
- black
  - Opinionated code formatter; automatically fixes issues.
- flake8
  - formatting checker and linter; does not automatically fix issues.

If an issue is detected when you run `git commit`, the action will be aborted and you'll receive a message about what needs to be fixed before committing.


* Minimum Python version: 3.8

* Install dependencies with `poetry install`. Don't have Poetry? Info here: https://poetry.eustace.io/

* Run `python manage.py makemigrations blossom` to build the migrations, then commit them to the database with `python manage.py migrate`.

* Run `python manage.py bootstrap` to prepopulate the site with the base posts. This will also create a base user account that you can use to make another user for yourself.

  * username: `blossom@grafeas.org`
  * password: `asdf`

You can use the above credentials to create yourself a new account.
* Navigate to `http://localhost:8000/superadmin/newuser` and log in with the above credentials.
* Create a personal user account with the requested fields. Make sure that you select "is superuser".

Next, we'll disable the default admin account.
* Navigate to `http://localhost:8000/superadmin/blossom/blossomuser/` and click on the "admin" user.
* Scroll to the bottom of the page and deselect "Active".
* Click Save.

You are now the only admin for the site. Other users must be added through the original form that can be accessed through the link above. 

Run the server with `python manage.py runserver`. Note: you should see in your logs "Found local_settings.py -- loading and using!" _twice_. This is due to how Django's hot reloading feature works; it uses two threads, and each thread will trigger the message. This is expected.

## Preparing for deploy

Run `python manage.py makemigrations blossom && python manage.py migrate`

Run `python manage.py collectstatic` and answer 'yes' -- this will populate the /static/ endpoint with everything it needs. This is not needed in development, but without it nothing from the static folders will be served properly. It will create a new folder called 'static' in the application root, which is why the staticfiles development side is called 'static_dev'.

Run `python manage.py bootstrap` and see above for expected user credentials and user configuration.

---

## Important links

#### localhost:8000/

Site root.

#### localhost:8000/api/

API root.

#### localhost:8000/payments/

The processing url for Stripe.

#### localhost:8000/payments/ping/

Used by Bubbles for site isup checks.

#### localhost:8000/admin/

General site administration, open to all user accounts.

#### localhost:8000/superadmin/

User / post traditional admin. Requires staff acount.

#### localhost:8000/superadmin/newuser/

Create a new user for the site.

#### localhost:8000/newpost/

Create a new post for the site.

#### localhost:8000/api/swagger

The swagger API endpoint list.

#### localhost:8000/api/redoc

The same thing as swagger, just with a different layout.
