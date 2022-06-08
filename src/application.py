from flask import Flask
from flask import session
from flask import flash
from flask import Blueprint
from flask import g
from flask_simplelogin import SimpleLogin
import redis
from . import config
import hashlib
from flask_sslify import SSLify


# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]
ssl_keyfile = config.REDIS_CFG["ssl_keyfile"]
ssl_certfile = config.REDIS_CFG["ssl_certfile"]
ssl_cert_reqs = config.REDIS_CFG["ssl_cert_reqs"]
ssl_ca_certs = config.REDIS_CFG["ssl_ca_certs"]

conn = redis.StrictRedis(host=host, 
                            port=port, 
                            password=pwd, 
                            db=0,
                            ssl=True,
                            ssl_keyfile=ssl_keyfile,
                            ssl_certfile=ssl_certfile,
                            ssl_ca_certs=ssl_ca_certs,
                            ssl_cert_reqs=ssl_cert_reqs, 
                            decode_responses=True)


def create_app():
    app = Flask(__name__, template_folder="templates")
    #sslify = SSLify(app)

    app.debug = True
    app.secret_key = 'vsfjnsrbnsvòojfnvòsojdfnvosf'
    app.config['SIMPLELOGIN_LOGIN_URL'] = '/login'
    #app.config['SIMPLELOGIN_LOGOUT_URL'] = '/logout'
    app.config['SIMPLELOGIN_HOME_URL'] = '/browse'
    app.config.from_pyfile('config.py')    

    simple_login = SimpleLogin(app, login_checker=check_my_users)

    # do Redis initializations
    init_db()

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .app import app as main_blueprint
    app.register_blueprint(main_blueprint)

    # blueprint for admin parts
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    return app

def init_db():
    print("Initializing Redis...")
    #conn.ft().config_set("DEFAULT_DIALECT", 2)


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