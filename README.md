# blossom

![Image of Blossom, from 1998's Powerpuff Girls](https://vignette.wikia.nocookie.net/powerpuff/images/2/23/Blossom-pic.png/revision/latest?cb=20190329151816)

The website. The app. The everything. MUST REMAIN PRIVATE.

A Django app that, right now, is our website, payment portal for donations, engineering blog, and API.

## Local development

### NOTE FOR OSX:

OSX does not route .localhost domains correctly, so in order to work with the API, you'll have to modify your hosts file. Edit /etc/hosts to add the following line at the bottom:

```
127.0.0.1	api.grafeas.localhost
127.0.0.1	wiki.grafeas.localhost
```

Flush the DNS cache with `sudo dscacheutil -flushcache`; then requests to the local version of the api (for example, "http://api.grafeas.localhost:8000/submissions/", should work.)

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
# this requires that you use "grafeas.localhost:8000" as your method for accessing
# the site.
# ALLOWED_HOSTS = ['.grafeas.localhost', 'grafeas.localhost', 'wiki.grafeas.localhost']
ALLOWED_HOSTS = ['*']
SESSION_COOKIE_DOMAIN = "grafeas.localhost"
PARENT_HOST = 'grafeas.localhost:8000'

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
```
This file will be ignored by git, so make any changes you need to while developing.

## Notes on URLs

Because there are subdomains that share a common session cookie, using `localhost:8000` as the development URL isn't an option because of some legacy issues with how the internet works. In Chrome, ending any URL with `.localhost` will automatically loop back to the host computer, so you don't have to modify your `hosts` file. Make sure that when you're working with the application, you're using `grafeas.localhost:8000` as the base url; for example, `wiki.grafeas.localhost:8000` or `payments.grafeas.localhost:8000`. This will translate to `grafeas.org` when deployed, so verify that anything that needs to be cross-subdomain is able to tell what the base host is.


* Minimum Python version: 3.8

* In order to get the wiki to work, there are some extra system dependencies that need to be installed. 
  * OSX: Download and install this: `http://ethan.tira-thompson.com/Mac_OS_X_Ports_files/libjpeg-libpng%20%28universal%29.dmg` (more information here: https://django-wiki.readthedocs.io/en/latest/installation.html#mac-os-x-10-5)
  * Debian / Ubuntu: `sudo apt-get install libjpeg8 libjpeg-dev libpng12-0 libpng12-dev`

* Install dependencies with `poetry install`. Don't have Poetry? Info here: https://poetry.eustace.io/

* Run `python manage.py makemigrations blossom` to build the migrations, then commit them to the database with `python manage.py migrate --settings=blossom.local_settings`.

* Run `python manage.py bootstrap --settings=blossom.local_settings` to prepopulate the site with the base posts. This will also create a base user account that you can use to make another user for yourself.

  * username: `blossom@grafeas.org`
  * password: `asdf`

You can use the above credentials to create yourself a new account.
* Navigate to http://grafeas.localhost:8000/superadmin/newuser and log in with the above credentials.
* Create a personal user account with the requested fields. Make sure that you select "is superuser".

Next, we'll disable the default admin account.
* Navigate to http://grafeas.localhost:8000/superadmin/blossom/blossomuser/ and click on the "admin" user.
* Scroll to the bottom of the page and deselect "Active".
* Click Save.

You are now the only admin for the site. Other users must be added through the original form that can be accessed through the link above. 

Run the server with `python manage.py runserver --settings=blossom.local_settings` Any time you need to run a django command that will affect the database when running locally, always end it with `--settings=blossom.local_settings`.

## Preparing for deploy

Run `python manage.py makemigrations blossom && python manage.py migrate`

Run `python manage.py collectstatic` and answer 'yes' -- this will populate the /static/ endpoint with everything it needs. This is not needed in development, but without it nothing from the static folders will be served properly. It will create a new folder called 'static' in the application root, which is why the staticfiles development side is called 'static_dev'.

Run `python manage.py bootstrap` and see above for expected user credentials and user configuration.

---

## Important links

#### payments.grafeas.localhost:8000

The processing url for Stripe.

#### payments.grafeas.localhost:8000/ping

Used by Bubbles for site isup checks.

#### grafeas.localhost:8000

Site root.

#### grafeas.localhost:8000/admin/

General site administration, open to all user accounts.

#### grafeas.localhost:8000/superadmin/

User / post traditional admin. Requires staff acount.

#### grafeas.localhost:8000/superadmin/newuser

Create a new user for the site.

#### grafeas.localhost:8000/newpost

Create a new post for the site.

#### wiki.grafeas.localhost:8000/

Root for wiki.

#### api.grafeas.localhost:8000/swagger

The swagger API endpoint list.

#### api.grafeas.localhost:8000/redoc

The same thing as swagger, just with a different layout.
