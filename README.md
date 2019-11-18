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

This file will be ignored by git, so make any changes you need to while developing.

Run the server with `python manage.py runserver --settings=blossom.local_settings`

Any time you need to run a django command when running locally, always end it with `--settings=blossom.local_settings`.

## Preparing for deploy

Run `python manage.py collectstatic` and answer 'yes' -- this will populate the /static/ endpoint with everything it needs. This is not needed in development, but without it nothing from the static folders will be served properly. It will create a new folder called 'static' in the application root, which is why the staticfiles development side is called 'static_dev'.
