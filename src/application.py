#from . import config
from config import get_db, okta
import hashlib
#from flask_oidc import OpenIDConnect
from okta.client import Client as UsersClient

import secrets
import requests
import base64
from user import User, Role

import flask
from flask import Flask, flash, Blueprint, g, render_template, redirect, request, session, url_for
from flask_cors import CORS
from flask_login import (LoginManager,current_user,login_required,login_user,logout_user,)

def create_app():
    app = Flask(__name__, template_folder="templates")

    app.config["SESSION_TYPE"] = "filesystem"
    app.config.update({'SECRET_KEY': secrets.token_hex(64)})
    CORS(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    # do Redis initializations
    init_db()

    # blueprint for bookmark routes in our app
    from .bookmark import bookmrk as bookmark_blueprint
    app.register_blueprint(bookmark_blueprint)

    # blueprint for draft routes in our app
    from .draft import draft as draft_blueprint
    app.register_blueprint(draft_blueprint)

    # blueprint for non-auth parts of app
    from .app import app as main_blueprint
    app.register_blueprint(main_blueprint)

    # blueprint for analytics
    from .analytics import analytic as analytic_blueprint
    app.register_blueprint(analytic_blueprint)

    # blueprint for admin parts
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    @app.route("/login")
    def login():
        # store app state and code verifier in session
        session['app_state'] = secrets.token_urlsafe(64)
        session['code_verifier'] = secrets.token_urlsafe(64)
        session.permanent = True

        # calculate code challenge
        hashed = hashlib.sha256(session['code_verifier'].encode('ascii')).digest()
        encoded = base64.urlsafe_b64encode(hashed)
        code_challenge = encoded.decode('ascii').strip('=')

        # get request params
        query_params = {'client_id': okta["client_id"],
                        'redirect_uri': okta["redirect_uri"],
                        'scope': "openid email profile",
                        'state': session['app_state'],
                        'code_challenge': code_challenge,
                        'code_challenge_method': 'S256',
                        'response_type': 'code',
                        'response_mode': 'query'}

        # build request_uri
        request_uri = "{base_url}?{query_params}".format(
            base_url=okta["auth_uri"],
            query_params=requests.compat.urlencode(query_params)
        )

        return redirect(request_uri)


    @app.before_request
    def check_valid_login():
        # Store visits in a time series visited pages
        if current_user.is_authenticated and request.endpoint != "static":
            get_db().ts().add("keybase:visits", "*", 1, duplicate_policy='first')

        # save wanted url if not authenticated
        if request.endpoint == "app.doc" and not current_user.is_authenticated:
            print("post-login doc is " + request.path)
            flash(request.path, 'wanted')

        # endpoints used for authentication
        endpoint_group = ('static', 'login', 'callback')
        if not request.endpoint in endpoint_group and not current_user.is_authenticated:
            return render_template('index.html', next=request.endpoint)


    @app.errorhandler(404)
    def page_not_found(error):
        return redirect(url_for('app.index'))


    @app.route("/authorization-code/callback")
    def callback():
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        code = request.args.get("code")
        app_state = request.args.get("state")

        try:
            print("Session token has been read")
        except:
            print("Cannot read session token")

        try:
            if app_state != session['app_state']:
                return "The app state does not match"
            if not code:
                return "The code was not returned or is not accessible", 403
        except KeyError:
            print("KeyError error: app_state missing")
            return redirect(url_for('app.index'))

        query_params = {'grant_type': 'authorization_code',
                        'code': code,
                        'redirect_uri': request.base_url,
                        'code_verifier': session['code_verifier'],
                        }
        query_params = requests.compat.urlencode(query_params)
        exchange = requests.post(
            okta["token_uri"],
            headers=headers,
            data=query_params,
            auth=(okta["client_id"], okta["client_secret"]),
        ).json()

        # Get tokens and validate
        if not exchange.get("token_type"):
                return "Unsupported token type. Should be 'Bearer'.", 403
        access_token = exchange["access_token"]

        # Authorization flow successful, get userinfo and login user
        userinfo_response = requests.get(okta["userinfo_uri"], 
                                        headers={'Authorization': f'Bearer {access_token}'}).json()

        unique_id = userinfo_response["sub"]
        user_email = userinfo_response["email"]
        user_given_name = userinfo_response["given_name"]
        user_name = userinfo_response["name"]

        user = None
        if not User.exists(unique_id):
            # default user is a viewer
            user = User.create(unique_id, user_given_name, user_name, user_email)
        else:
            user = User.update(unique_id, user_given_name, user_name, user_email)

        # Now create the session
        login_user(user)

        # Store authentications in a time series
        get_db().ts().add("keybase:authentications", "*", 1, duplicate_policy='first')

        # Check desired url
        wanted = flask.get_flashed_messages(category_filter=["wanted"])
        if len(wanted):
            print("wanted is " + wanted[0])
            return redirect(wanted[0])

        return redirect(url_for("app.browse"))

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        logout_user()
        return redirect(url_for('app.index'))

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        return redirect(url_for('app.index'))

    return app


def getUserGroups():
    # Get groups
    # https://developer.okta.com/docs/guides/create-an-api-token/main/
    # Tokens are valid for 30 days from creation or last use
    api_token = okta["api_token"]
    usergroups_response = requests.get(okta["groups_uri"].format(unique_id), 
                                        headers={'Accept':'application/json',
                                                'Content-Type':'application/json',
                                                'Authorization': f'SSWS {api_token}'}).json()

    print(usergroups_response)


def init_db():
    print("Initializing Redis...")
    #conn.ft().config_set("DEFAULT_DIALECT", 2)

"""


def check_my_users(user):
    credentials = conn.hmget("keybase:user:{}".format(user["username"].lower()), ['password', 'status'])
    psw = credentials[0]
    status = credentials[1]

    if (psw == None):
        flash('Please check your login details and try again.')
        return False
    elif (status != "enabled"):
        flash('Your account is disabled')
        return False # if the user is not enabled, reload the page
    elif (hashlib.sha256(user["password"].encode()).hexdigest() != psw):
        flash('Please check your password.')
        return False

    # if the above check passes, then we know the user has the right credentials
    session['username'] = user["username"].lower()
    return True
"""


