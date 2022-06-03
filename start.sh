#!/bin/sh

export FLASK_APP=src/__init__.py
export FLASK_ENV=development
#flask run --port=443 --cert=adhoc --host=0.0.0.0 &
flask run --host=0.0.0.0 &
