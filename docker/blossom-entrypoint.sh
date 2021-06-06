#!/usr/bin/env bash
set -euo pipefail

if [ "$1" = "runserver" ]; then
  python manage.py migrate
  python manage.py bootstrap_site
  python manage.py collectstatic --noinput -v 0

  gunicorn -c ./blossom/instrumentation.py --access-logfile - --workers 3 --bind "0.0.0.0:${PORT}" blossom.wsgi:application
  # python manage.py runserver "0.0.0.0:${PORT}"
fi
