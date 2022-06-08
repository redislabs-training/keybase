#!/bin/sh

export FLASK_APP=src/__init__.py
export FLASK_ENV=development
#flask run --port=443 --cert=adhoc --host=0.0.0.0 &
#gunicorn --workers 4 --bind 0.0.0.0:5000 "wsgi:create_app()"
flask run --host=0.0.0.0 &
