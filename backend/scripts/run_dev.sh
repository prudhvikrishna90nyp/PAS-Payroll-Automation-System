#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python manage.py migrate
python manage.py runserver
