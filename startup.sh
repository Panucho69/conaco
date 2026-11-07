#!/bin/sh
# Arranque en producción (Azure App Service): aplica migraciones y levanta gunicorn.
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Copia las fotos que vienen con el código a la carpeta permanente, sin pisar las que ya existan
if [ -n "$DJANGO_MEDIA_ROOT" ] && [ -d media ]; then
    mkdir -p "$DJANGO_MEDIA_ROOT"
    cp -rn media/. "$DJANGO_MEDIA_ROOT"/
fi

# --access-logfile - deja cada visita (método, ruta y código) en el Log stream de Azure
gunicorn canaco.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile -
