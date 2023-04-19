import flask
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import (login_required)
from flask_paginate import Pagination, get_page_args
import redis
from redis.commands.search.query import Query
import json
import base64

from src.common.utils import ShortUuidPk, parse_query_string
from src.document.document import Document
from src.common.utils import requires_access_level, Role, get_db
from src.common.config import REDIS_CFG

admin_bp = Blueprint('admin_bp', __name__,
                     template_folder='./templates')


@admin_bp.route('/tools', methods=['GET', 'POST'])
@login_required
@requires_access_level(Role.ADMIN)
def tools():
    title = "Admin functions"
    desc = "Admin functions"
    key = []
    name = []
    group = []
    email = []
    users = None
    role, rolefilter, queryfilter = "all", "", "*"

    if flask.request.method == 'POST':
        if request.form['role']:
            role = request.form['role']
            if role != "all":
                rolefilter = " @group:{" + role + "}"
                queryfilter = ""

        if request.form['q']:
            queryfilter = parse_query_string(request.form['q'])

    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    rs = get_db().ft("user_idx").search(
        Query(queryfilter + rolefilter)
        .return_field("name")
        .return_field("group")
        .return_field("email")
        .sort_by("name", asc=True)
        .paging(offset, per_page))

    pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                            bulma_style='small', prev_label='Previous', next_label='Next page')

    if (rs is not None) and len(rs.docs):
        for doc in rs.docs:
            key.append(doc.id.split(':')[-1])
            name.append(doc.name)
            group.append(doc.group)
            email.append(doc.email)

        users = zip(key, name, group, email)

    return render_template('admin.html', title=title, desc=desc, users=users, pagination=pagination, role=role)


@admin_bp.route('/tags')
@login_required
@requires_access_level(Role.ADMIN)
def tags():
    title = "Admin functions"
    desc = "Admin functions"

    # Fetching list of tags and categories
    categories = get_db().hgetall("keybase:categories")
    tags = get_db().hgetall("keybase:tags")
    return render_template('tags.html', title=title, desc=desc, tags=tags, categories=categories)


@admin_bp.route('/tagsearch', methods=['GET'])
@login_required
@requires_access_level(Role.EDITOR)
def tagsearch():
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
    if get_db().hexists("keybase:tags", request.form['tag'].lower().replace(" ", "")):
        return redirect(url_for('admin_bp.tags'))

    # Add lowercase tag and description
    if len(request.form['tag']) > 1:
        tag = {request.form['tag'].lower().replace(" ", ""): request.form['description']}
        get_db().hset("keybase:tags", mapping=tag)

    return redirect(url_for('admin_bp.tags'))


@admin_bp.route('/createcategory', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def createcategory():
    if len(request.form['category']) > 1:
        pkcreator = ShortUuidPk()
        category = {pkcreator.create_pk(): request.form['category']}
        get_db().hset("keybase:categories", mapping=category)
    else:
        return jsonify(message="Metadata is missing", code="success"), 500

    return redirect(url_for('admin_bp.tags'))


@admin_bp.route('/data')
@login_required
@requires_access_level(Role.ADMIN)
def data():
    title = "Admin functions"
    desc = "Admin functions"

    return render_template('data.html', title=title, desc=desc)


@admin_bp.route('/backup', methods=['GET'])
@login_required
@requires_access_level(Role.ADMIN)
def backup():
    result = []
    backup = ""
    cursor = 0

    while True:
        cursor, keys = get_db(decode=False).scan(cursor, match='keybase*', count=20, _type="HASH")
        result.extend(keys)
        for key in keys:
            hashdata = get_db(decode=False).hgetall(key)
            data = {}
            thevalue = {}
            data['key'] = key.decode("utf-8")
            for (field, value) in hashdata.items():
                thevalue[base64.b64encode(field).decode('ascii')] = base64.b64encode(value).decode('ascii')

            data['value'] = thevalue
            backup += json.dumps(data) + "\n"

        if cursor == 0:
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
        hashdata = {}
        print(data['key'])
        for (field, value) in data['value'].items():
            hashdata[base64.b64decode(field.encode('ascii'))] = base64.b64decode(value.encode('ascii'))
        get_db(decode=False).hmset(data['key'], hashdata)

    return jsonify(message="Restore done")


@admin_bp.route('/jimport', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def jimport():
    print("Starting to import to Json")
    uploaded_file = request.files['file']
    print(uploaded_file.filename)
    cnt = 0
    for line in uploaded_file:
        data = json.loads(line)
        if "keybase:kb:" in data['key']:
            cnt = cnt + 1
            # print(str(cnt) + ": " + data['key'])
            name, content, tags, state, owner, author = "", "", "", "", "", ""
            creation, update = 0, 0
            for (field, value) in data['value'].items():
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'name':
                    name = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'content':
                    content = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'creation':
                    creation = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'update':
                    update = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'tags':
                    tags = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'owner':
                    owner = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'author':
                    author = base64.b64decode(value.encode('ascii'))
                if base64.b64decode(field.encode('ascii')).decode('utf-8') == 'state':
                    state = base64.b64decode(value.encode('ascii'))
                # hash[base64.b64decode(field.encode('ascii'))] = base64.b64decode(value.encode('ascii'))
            # use data['key'] as keyname
            doc = Document(
                pk=data['key'].split(':')[-1],
                name=name,
                content=content,
                creation=creation,
                last=update,
                processable=1,
                state=state,
                owner=owner,
                tags=tags,
                author=author,
                versions=[]
            )
            #doc.set_name = "keybase:json:" + data['key'].split(':')[-1]
            doc.save()

    return jsonify(message="Restore done")


@admin_bp.route('/group', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def group():
    # TODO Check the user exists and the role is valid
    print("Setting role of " + request.form['id'] + " to " + request.form['group'])
    get_db().hmset("keybase:okta:{}".format(request.form['id']), {"group": request.form['group']})
    return jsonify(message="Role updated")
