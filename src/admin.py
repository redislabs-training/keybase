from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash, session
from flask import current_app
import redis
from redis import RedisError
from . import config
import time
import hashlib
from flask_simplelogin import is_logged_in

admin = Blueprint('admin', __name__)

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]
pool = redis.ConnectionPool(host=host, port=port, password=pwd, db=0, decode_responses=True)
conn = redis.Redis(connection_pool=pool)


@admin.before_request
def handle_user_loading_here_or_something():
    if is_logged_in():
        print("logged in")
    else:
        print("NOT logged in")
        TITLE="About keybase"
        DESC="About keybase"
        return render_template('about.html', title=TITLE, desc=DESC)


@admin.route('/list')
def list():
    print("loading the list")
    TITLE="About keybase"
    DESC="About keybase"
    return render_template('about.html', title=TITLE, desc=DESC)