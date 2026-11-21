#!/bin/sh
# Przy każdym starcie kontenera: migracje i pliki statyczne (nginx na hoście serwuje ./public/static).
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
