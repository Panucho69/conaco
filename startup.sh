#!/bin/sh
# Arranque en producción (Azure App Service): aplica migraciones y levanta gunicorn.
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn canaco.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
