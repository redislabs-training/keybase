from flask import Flask, flash, Blueprint, g, render_template, redirect, request, session, url_for
from flask_login import (LoginManager, current_user, login_required)
import hashlib, time

from src.user import User
from src.common.config import get_db

auth_bp = Blueprint('auth_bp', __name__,
                    template_folder='./templates')

login_manager = LoginManager()


@auth_bp.record_once
def on_load(state):
    login_manager.init_app(state.app)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@login_manager.unauthorized_handler
def unauthorized_callback():
    if not current_user.is_authenticated:
        if request.endpoint == "document_bp.doc" and not current_user.is_authenticated:
            print("post-login doc is " + request.path)
            flash(request.path, 'wanted')
        return render_template('index.html', next=request.endpoint)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_post():
    if current_user.is_authenticated:
        return redirect(url_for('document_bp.browse'))

    username = request.form.get('username')
    print(username)
    password = hashlib.sha256(request.form.get('password').encode()).hexdigest()

    user = get_db().hmget("keybase:user:{}".format(username), ['password', 'status'])
    psw = user[0]
    status = user[1]

    if psw is None:
        flash('Please check your login details and try again')
        return redirect(
            url_for('auth_bp.login_post'))  # if the user doesn't exist or password is wrong, reload the page
    elif status != "enabled":
        flash('Your account is disabled')
        return redirect(url_for('auth_bp.login_post'))  # if the user is not enabled, reload the page
    elif password != psw:
        flash('Please check your password')
        return redirect(
            url_for('auth_bp.login_post'))  # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, authenticate the user

    return redirect(url_for('document_bp.browse'))


@auth_bp.route('/signup')
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('document_bp.browse'))
    else:
        return render_template('signup.html')


@auth_bp.route('/update', methods=['POST'])
@login_required
def update():
    currentpsw = get_db().hget("keybase:user:{}".format(session['username']), "password")
    if (currentpsw != hashlib.sha256(request.form.get('currentpassword').encode()).hexdigest()):
        flash('Your current password is incorrect', 'error')
    elif ((not len(request.form.get('newpassword'))) or (not len(request.form.get('repeatpassword')))):
        flash('Empty password', 'error')
    elif (request.form.get('newpassword') != request.form.get('repeatpassword')):
        flash('Passwords are different', 'error')
    elif (len(request.form.get('newpassword')) < 8):
        flash('Password is too short (>8)', 'error')
    else:
        newpassword = hashlib.sha256(request.form.get('newpassword').encode()).hexdigest()
        get_db().hset("keybase:user:{}".format(session['username']), "password", newpassword)
        flash('Passwords changed', 'message')
    return redirect(url_for('app.profile'))


@auth_bp.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = hashlib.sha256(request.form.get('password').encode()).hexdigest()

    # Check mail, username and password
    # ...

    # Check username not too short
    if (len(name) < 7):
        flash('Username is too short')
        return redirect(url_for('auth.signup'))

    # Check password not too short
    if (len(request.form.get('password')) < 8):
        flash('Password is too short')
        return redirect(url_for('auth.signup'))

    # Check username does not exist
    user = get_db().hgetall("keybase:user:{}".format(name))
    if (user):
        flash('Username already exists')
        return redirect(url_for('auth.signup'))

    # Check username does not exist
    mail = get_db().zrank("keybase:mails", email)
    if (mail == 0):
        flash('Email already exists')
        return redirect(url_for('auth.signup'))

    # Now add the user, lowercase
    pipeline = get_db().pipeline(True)
    pipeline.hmset("keybase:user:{}".format(name.lower()), {
        'mail': email,
        'password': password,
        'status': "disabled",
        'signup': time.time()})
    pipeline.zadd("keybase:mails", {email: 0})
    pipeline.execute()

    return redirect(url_for('auth.login'))
