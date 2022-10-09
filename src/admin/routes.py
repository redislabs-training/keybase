from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import (current_user, login_required)
import redis
from redis.commands.search.query import Query
import json
import base64

from src.user import requires_access_level, Role
from src.common.config import get_db, REDIS_CFG

admin_bp = Blueprint(   'admin_bp', __name__,
                        template_folder='./templates')


@admin_bp.before_request
def check_valid_login():
    if not current_user.is_authenticated:
        return render_template('index.html')


# Database Connection
host = REDIS_CFG["host"]
port = REDIS_CFG["port"]
pwd = REDIS_CFG["password"]
ssl = REDIS_CFG["ssl"]
ssl_keyfile = REDIS_CFG["ssl_keyfile"]
ssl_certfile = REDIS_CFG["ssl_certfile"]
ssl_cert_reqs = REDIS_CFG["ssl_cert_reqs"]
ssl_ca_certs = REDIS_CFG["ssl_ca_certs"]

conn = redis.StrictRedis(host=host,
                         port=port,
                         password=pwd,
                         db=0,
                         ssl=ssl,
                         ssl_keyfile=ssl_keyfile,
                         ssl_certfile=ssl_certfile,
                         ssl_ca_certs=ssl_ca_certs,
                         ssl_cert_reqs=ssl_cert_reqs,
                         decode_responses=False)


@admin_bp.route('/tools')
@login_required
@requires_access_level(Role.ADMIN)
def tools():
    TITLE = "Admin functions"
    DESC = "Admin functions"
    key = []
    name = []
    group = []
    email = []

    rs = get_db().ft("user_idx").search(
        Query("*").return_field("name").return_field("group").return_field("email").paging(0, 100))
    for doc in rs.docs:
        key.append(doc.id.split(':')[-1])
        name.append(doc.name)
        group.append(doc.group)
        email.append(doc.email)

    users = zip(key, name, group, email)
    return render_template('admin.html', title=TITLE, desc=DESC, users=users)


@admin_bp.route('/tags')
@login_required
@requires_access_level(Role.ADMIN)
def tags():
    TITLE = "Admin functions"
    DESC = "Admin functions"
    tags = []

    # Fetching list of tags
    cursor, fields = get_db().hscan("keybase:tags", 0, count=200)
    for tag in fields:
        tags.append(tag)

    return render_template('tags.html', title=TITLE, desc=DESC, tags=tags)


@admin_bp.route('/tagsearch', methods=['GET'])
@login_required
@requires_access_level(Role.EDITOR)
def tagsearch():
    TITLE = "Admin functions"
    DESC = "Admin functions"
    tags = []

    # Fetching list of tags
    cursor, fields = get_db().hscan("keybase:tags", 0, match="*" + request.args.get('q') + "*", count=200)
    for tag in fields:
        tags.append(tag)

    return jsonify(matching_results=tags)


@admin_bp.route('/tag', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def tag():
    TITLE = "Admin functions"
    DESC = "Admin functions"

    if get_db().hexists("keybase:tags", request.form['tag'].lower().replace(" ", "")):
        return redirect(url_for('admin_bp.tags'))

    # Add lowercase tag and description
    if len(request.form['tag']) > 1:
        tag = {request.form['tag'].lower().replace(" ", ""): request.form['description']}
        get_db().hmset("keybase:tags", tag)

    return redirect(url_for('admin_bp.tags'))


@admin_bp.route('/data')
@login_required
@requires_access_level(Role.ADMIN)
def data():
    TITLE = "Admin functions"
    DESC = "Admin functions"

    return render_template('data.html', title=TITLE, desc=DESC)


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


@admin_bp.route('/backup', methods=['GET'])
@login_required
@requires_access_level(Role.ADMIN)
def backup():
    result = []
    backup = ""
    cursor = 0

    while True:
        cursor, keys = conn.scan(cursor, match='keybase*', count=20, _type="HASH")
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

        if (cursor == 0):
            break

    return jsonify(message="Backup created", backup=backup)


@admin_bp.route('/restore', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
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


@admin_bp.route('/group', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def group():
    # TODO Check the user exists and the role is valid
    print("Setting role of " + request.form['id'] + " to " + request.form['group'])
    get_db().hmset("keybase:okta:{}".format(request.form['id']), {"group": request.form['group']})
    return jsonify(message="Role updated")