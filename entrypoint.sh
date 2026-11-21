#!/bin/sh
# Przy każdym starcie kontenera: migracje, pliki statyczne (nginx na hoście serwuje ./public/static),
# model kompetencji (tylko gdy brak) i przebudowa wbudowanej bazy wiedzy z docs_assets.
# Źródeł dodanych przez urzędy w panelu „Baza wiedzy” przebudowa nie zmienia.
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py import_competency_model --if-missing
python manage.py ingest_legal_docs
exec "$@"
