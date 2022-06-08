from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash, session, jsonify
from flask import current_app
import redis
from redis import RedisError
from . import config
import json
import time
import urllib.parse
from flask_simplelogin import is_logged_in, login_required
import base64


admin = Blueprint('admin', __name__)

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]
ssl = config.REDIS_CFG["ssl"]
ssl_keyfile = config.REDIS_CFG["ssl_keyfile"]
ssl_certfile = config.REDIS_CFG["ssl_certfile"]
ssl_cert_reqs = config.REDIS_CFG["ssl_cert_reqs"]
ssl_ca_certs = config.REDIS_CFG["ssl_ca_certs"]

conn = redis.StrictRedis(host=host, 
                            port=port, 
                            password=pwd, 
                            db=0,
                            ssl=ssl,
                            ssl_keyfile=ssl_keyfile,
                            ssl_certfile=ssl_certfile,
                            ssl_ca_certs=ssl_ca_certs,
                            ssl_cert_reqs=ssl_cert_reqs, 
                            decode_responses=True)

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

"""
# Routines to backup and restore encoding data as UTF-8. Cannot encode binary vector embeddings, so to use vector similarity, I choose base64 encoding
# These routines could be reused to produce statements such as HSET ..., in a much more readable format
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
            data = ObjDict()
            data['key'] = key.decode('utf-8')
            data['type'] = "hash"
            theValue = ObjDict()
            for (field, value) in hash.items():
                if (field.decode('utf-8') == "content_embedding"):
                #    theValue[field.decode("utf-8")] = str(value)
                    continue
                theValue[field.decode("utf-8")] = value.decode("utf-8")
            data['value'] = theValue
            backup += json.dumps(data) + "\n"

        if (cursor==0):
            break

    return jsonify(message="Backup created", backup=backup)


@admin.route('/restore', methods=['POST'])
def restore():
    print("Starting to restore")
    uploaded_file = request.files['file']
    print(uploaded_file.filename)
    #conn.execute_command("HSET minestra patata \"dieci l'anno\" carote \"sette quasi\" zucchine 8")
    for line in uploaded_file:
        data = json.loads(line.decode('utf-8'))
        if (data['type'] == "hash"):
            conn.hmset(data['key'], data['value'])

    return jsonify(message="Restore done")
"""

@admin.route('/backup', methods=['GET'])
def backup():
    result = []
    backup = ""
    cursor=0

    while True:
        cursor, keys  = conn.scan(cursor, match='keybase*', count=20, _type="HASH")
        result.extend(keys)
        for key in keys:
            hash = conn.hgetall(key)
            data = {}
            theValue = {}
            data['key'] = key.decode("utf-8")
            for (field, value) in hash.items():
                theValue[base64.b64encode(field).decode('ascii')] = base64.b64encode(value).decode('ascii')

            data['value'] = theValue
            backup += json.dumps(data) + "\n"

        if (cursor==0):
            break

    return jsonify(message="Backup created", backup=backup)


@admin.route('/restore', methods=['POST'])
def restore():
    print("Starting to restore")
    uploaded_file = request.files['file']
    print(uploaded_file.filename)
    for line in uploaded_file:
        data = json.loads(line)
        hash = {}
        print(data['key'])
        for (field, value) in data['value'].items():
            hash[base64.b64decode(field.encode('ascii'))] = base64.b64decode(value.encode('ascii'))
        conn.hmset(data['key'], hash)

    return jsonify(message="Restore done")


@admin.route('/list')
def list():
    print("Loading the list of users")
    TITLE="List users"
    DESC="List users"
    return render_template('admin.html', title=TITLE, desc=DESC)