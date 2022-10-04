#!/bin/sh

export FLASK_APP=src/application.py
export FLASK_DEBUG=1
export PYTHONPATH=src/:src/common/
#flask run --port=443 --cert=adhoc --host=0.0.0.0 &
#gunicorn --workers 4 --bind 0.0.0.0:5000 "wsgi:create_app()"
flask run --host=0.0.0.0 &
