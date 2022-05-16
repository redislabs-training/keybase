from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash, session, jsonify
from flask import current_app
import redis
from redis import RedisError
from . import config
import time
import hashlib
import urllib.parse
from flask_simplelogin import is_logged_in, login_required

admin = Blueprint('admin', __name__)

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]
pool = redis.ConnectionPool(host=host, port=port, password=pwd, db=0, encoding='utf-8', decode_responses=False)
conn = redis.Redis(connection_pool=pool)


@admin.before_request
def handle_user_loading_here_or_something():
    if not is_logged_in():
        print("NOT logged in")
        TITLE="About keybase"
        DESC="About keybase"
        return render_template('index.html', title=TITLE, desc=DESC)

@admin.route('/')
def index():
    return render_template('admin.html')

@admin.route('/tools')
def tools():
    TITLE="Admin functions"
    DESC="Admin functions"
    return render_template('admin.html', title=TITLE, desc=DESC)

@admin.route('/backup', methods=['GET'])
def backup():
    result = []
    backup =""
    cursor=0

    while True:
        cursor, keys  = conn.scan(cursor, match='keybase*', count=2, _type="HASH")
        result.extend(keys)
        for key in keys:
            hash = conn.hgetall(key)
            #hash = conn.hmget(key, ['name', 'content', 'content_embedding'])
            command="HSET " + key.decode('utf-8')
            for (field, value) in hash.items():
                if (field.decode('utf-8') == "content_embedding"):
                    command += " " + '"{}"'.format(field.decode('utf-8')) + " " + str(value)[1:]
                else:
                    command += " " + '"{}"'.format(field.decode('utf-8')) + " " + '"{}"'.format(value.decode('utf-8').replace("\n", "\\n"))
            print ("--------> " + command)
            backup += command + "\n"

        if (cursor==0):
            break

    return jsonify(message="Backup created", backup=backup)


@admin.route('/restore', methods=['POST'])
def restore():
    print("Starting to restore")
    uploaded_file = request.files['file']
    print(uploaded_file.filename)
    for line in uploaded_file:
        print("Next line: " + str(line))

    return jsonify(message="Restore done")


@admin.route('/list')
def list():
    print("Loading the list of users")
    TITLE="List users"
    DESC="List users"
    return render_template('admin.html', title=TITLE, desc=DESC)