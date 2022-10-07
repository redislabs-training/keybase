#!/bin/sh

export FLASK_APP=src/application.py
export FLASK_DEBUG=1
export PYTHONPATH=src/

#gunicorn --workers 1 --bind 0.0.0.0:5000 "wsgi:create_app()"
flask run --host=0.0.0.0 &
