import flask
import flask_login
from flask import flash, Blueprint, render_template, redirect, request, session, url_for, jsonify
from flask_login import (LoginManager, current_user, login_required, logout_user)
import hashlib
import time
from flask import current_app
from flask_paginate import Pagination, get_page_args
from redis.commands.search.field import TextField, TagField
from redis.commands.search.indexDefinition import IndexDefinition
from redis.commands.search.query import Query

from src.auth.authuser import AuthUser
from src.common.utils import get_db, requires_access_level, Role, parse_query_string

auth_bp = Blueprint('auth_bp', __name__,
                    template_folder='./templates')

login_manager = LoginManager()

# default user is admin/admin
# HSET keybase:auth:admin username admin password 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918 status enabled group admin given_name "Administrator" name "Administrator"

@auth_bp.record_once
def on_load(state):
    login_manager.init_app(state.app)


@login_manager.user_loader
def load_user(user_id):
    return AuthUser.get(user_id)


@auth_bp.route('/users', methods=['GET', 'POST'])
@login_required
@requires_access_level(Role.ADMIN)
def users():
    title = "Admin functions"
    desc = "Admin functions"
    key = []
    name = []
    group = []
    email = []
    users = None
    role, rolefilter, queryfilter = "all", "", "*"

    # Reading the list of indexes for eventual creation
    indexes = get_db().execute_command("FT._LIST")

    if "auth_idx" not in indexes:
        current_app.logger.info("The index auth_idx does not exist, creating it")
        index_def = IndexDefinition(prefix=["keybase:auth"])
        schema = (TextField("name"), TagField("group"))
        get_db().ft('auth_idx').create_index(schema, definition=index_def)

    if flask.request.method == 'POST':
        if request.form['role']:
            role = request.form['role']
            if role != "all":
                rolefilter = " @group:{" + role + "}"
                queryfilter = ""

        if request.form['q']:
            queryfilter = parse_query_string(request.form['q'])

    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    rs = get_db().ft("auth_idx").search(
        Query(queryfilter + rolefilter)
        .return_field("name")
        .return_field("group")
        .sort_by("name", asc=True)
        .paging(offset, per_page))

    pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                            bulma_style='small', prev_label='Previous', next_label='Next page')

    if (rs is not None) and len(rs.docs):
        for doc in rs.docs:
            key.append(doc.id.split(':')[-1])
            name.append(doc.name)
            group.append(doc.group)
            email.append(doc.name)

        users = zip(key, name, group, email)

    return render_template('users.html', title=title, desc=desc, users=users, pagination=pagination, role=role)


@login_manager.unauthorized_handler
def unauthorized_callback():
    if not current_user.is_authenticated:
        if request.endpoint == "public_bp.kb" and not current_user.is_authenticated:
            print("post-login doc is " + request.path)
            flash(request.path, 'wanted')
        return render_template('index.html', next=request.endpoint), 401


@auth_bp.route('/login')
def login():
    return render_template('index.html')


@auth_bp.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    current_app.logger.info("Started authentication for " + request.form.get('username'))
    if current_user.is_authenticated:
        return redirect(url_for('document_bp.browse'))

    username = request.form.get('username')
    password = hashlib.sha256(request.form.get('password').encode()).hexdigest()

    user = get_db().hmget("keybase:auth:{}".format(username).lower(), ['password', 'status'])
    psw = user[0]
    status = user[1]

    if psw is None:
        flash('Please check your login details and try again')
        return redirect(url_for('auth_bp.login'))
    elif status != "enabled":
        flash('Your account is disabled')
        return redirect(url_for('auth_bp.login'))
    elif password != psw:
        flash('Please check your password')
        return redirect(url_for('auth_bp.login'))  # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, authenticate the user
    user = AuthUser.get(username)

    # Now create the session
    flask_login.login_user(user)

    # Log the event
    current_app.logger.info('User logged in successfully: {}'.format(current_user.id))

    # Store authentications in a time series
    get_db().ts().add("keybase:authentications", "*", 1, duplicate_policy='first')

    return redirect(url_for('document_bp.browse'))


@auth_bp.route('/update', methods=['POST'])
@login_required
def update():
    currentpsw = get_db().hget("keybase:auth:{}".format(session['username']), "password")
    if currentpsw != hashlib.sha256(request.form.get('currentpassword').encode()).hexdigest():
        flash('Your current password is incorrect', 'error')
    elif (not len(request.form.get('newpassword'))) or (not len(request.form.get('repeatpassword'))):
        flash('Empty password', 'error')
    elif request.form.get('newpassword') != request.form.get('repeatpassword'):
        flash('Passwords are different', 'error')
    elif len(request.form.get('newpassword')) < 8:
        flash('Password is too short (>8)', 'error')
    else:
        newpassword = hashlib.sha256(request.form.get('newpassword').encode()).hexdigest()
        get_db().hset("keybase:auth:{}".format(session['username']), "password", newpassword)
        flash('Passwords changed', 'message')
    return redirect(url_for('app.profile'))


@auth_bp.route('/adduser')
def adduser():
    return render_template('signup.html')

@auth_bp.route('/createuser', methods=['POST'])
def createuser():
    username = request.form.get('username')
    name = request.form.get('name')
    password = hashlib.sha256(request.form.get('password').encode()).hexdigest()

    # Check username not too short
    if len(username) < 7:
        flash('Username is too short')
        return redirect(url_for('auth_bp.adduser'))

    # Check display name not too short
    if len(name) < 7:
        flash('Display name is too short')
        return redirect(url_for('auth_bp.adduser'))

    # Check password not too short
    if len(request.form.get('password')) < 8:
        flash('Password is too short')
        return redirect(url_for('auth_bp.adduser'))

    # Check username does not exist
    user = get_db().exists("keybase:auth:{}".format(name))
    if user:
        flash('Username already exists')
        return redirect(url_for('auth_bp.adduser'))

    # Now add the user, lowercase
    get_db().hmset("keybase:auth:{}".format(name.lower()), {
        'username': username,
        'password': password,
        'name': name,
        'group': "viewer",
        'status': "enabled",
        'signup': time.time()})

    return redirect(url_for('auth_bp.users'))


@auth_bp.route('/group', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def authgroup():
    # TODO Check the user exists and the role is valid
    print("Setting role of " + request.form['id'] + " to " + request.form['group'])
    get_db().hmset("keybase:auth:{}".format(request.form['id']), {"group": request.form['group']})
    return jsonify(message="Role updated")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    current_app.logger.info('User logged out: {}'.format(current_user.id))
    logout_user()
    return redirect(url_for('public_bp.landing'))
