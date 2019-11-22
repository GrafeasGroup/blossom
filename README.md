# blossom

![Image of Blossom, from 1998's Powerpuff Girls](https://vignette.wikia.nocookie.net/powerpuff/images/2/23/Blossom-pic.png/revision/latest?cb=20190329151816)

The website. The app. The everything. MUST REMAIN PRIVATE.

A Django app that, right now, is just our website and payment portal for donations.

## Local development

Create a file under the top level `blossom` folder called `local_settings.py`. Populate it with the following:

```python
# noinspection PyUnresolvedReferences
from blossom.settings.local import *
import better_exceptions

# trust me, this will make your life better.
better_exceptions.MAX_LENGTH = None

# Use this file when developing locally -- it has some helpful additions which
# change how the server runs.

DEBUG = True
ALLOWED_HOSTS = ['*']

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
```

* Minimum Python version: 3.8

* Install dependencies with `poetry install`. Don't have Poetry? Info here: https://poetry.eustace.io/

* Run `python manage.py makemigrations blossom` to build the migrations, then commit them to the database with `python manage.py migrate --settings=blossom.local_settings`.

* Run `python manage.py bootstrap --settings=blossom.local_settings` to prepopulate the site with the base posts. This will also create a base user account that you can use to make another user for yourself.

  * username: `blossom@grafeas.org`
  * password: `asdf`

You can use the above credentials to create yourself a new account.
* Navigate to http://localhost:8000/superadmin/newuser and log in with the above credentials.
* Create a personal user account with the requested fields. Make sure that you select "is superuser".

Next, we'll disable the default admin account.
* Navigate to http://localhost:8000/superadmin/blossom/blossomuser/ and click on the "admin" user.
* Scroll to the bottom of the page and deselect "Active".
* Click Save.

You are now the only admin for the site. Other users must be added through the original form that 

This file will be ignored by git, so make any changes you need to while developing.

Run the server with `python manage.py runserver --settings=blossom.local_settings` Any time you need to run a django command that will affect the database when running locally, always end it with `--settings=blossom.local_settings`.

## Preparing for deploy

Run `python manage.py makemigrations blossom && python manage.py migrate`

Run `python manage.py collectstatic` and answer 'yes' -- this will populate the /static/ endpoint with everything it needs. This is not needed in development, but without it nothing from the static folders will be served properly. It will create a new folder called 'static' in the application root, which is why the staticfiles development side is called 'static_dev'.

Run `python manage.py bootstrap` and see above for expected user credentials and user configuration.

---

## Important links

#### payments.localhost:8000

The processing url for Stripe.

#### payments.localhost:8000/ping

Used by Bubbles for site isup checks.

#### localhost:8000

Site root.

#### localhost:8000/admin/

General site administration, open to all user accounts.

#### localhost:8000/superadmin/

User / post traditional admin. Requires staff acount.

#### localhost:8000/superadmin/newuser

Create a new user for the site.

#### localhost:8000/newpost

Create a new post for the site.
