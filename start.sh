#!/bin/sh

#source /Users/mortensi/Google\ Drive/My\ Drive/Projects/webgames/webgamesvenv/bin/activate
export FLASK_APP=src/__init__.py
export FLASK_ENV=development
flask run &
