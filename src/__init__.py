from flask import Flask
from flask import session
from flask import flash
from flask import Blueprint
from flask import g
from flask_simplelogin import SimpleLogin
import redis
from . import config
# https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login
# https://hackersandslackers.com/your-first-flask-application
# https://www.reddit.com/r/flask/comments/b6yf7o/flasklogin_redis/
# https://flask-simple-login.readthedocs.io/en/latest/
# https://towardsdatascience.com/creating-restful-apis-using-flask-and-python-655bad51b24
# https://dev.opera.com/articles/html5-canvas-painting/

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]
#conn = redis.Redis(host=host, port=port, password=pwd, charset="utf-8", decode_responses=True)
pool = redis.ConnectionPool(host=host, port=port, password=pwd, db=0, decode_responses=True)
conn = redis.Redis(connection_pool=pool)

global globalredispool

def create_app():
    app = Flask(__name__, template_folder="templates")

    app.debug = True
    app.secret_key = 'vsfjnsrbnsvòojfnvòsojdfnvosf'
    app.config['SIMPLELOGIN_LOGIN_URL'] = '/login'
    #app.config['SIMPLELOGIN_LOGOUT_URL'] = '/logout'
    app.config['SIMPLELOGIN_HOME_URL'] = '/browse'
    app.config.from_pyfile('config.py')    

    simple_login = SimpleLogin(app, login_checker=check_my_users)

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .app import app as main_blueprint
    app.register_blueprint(main_blueprint)

    return app


def check_my_users(user):
    psw = conn.hget("user:{}".format(user["username"].lower()), "password")

    if (psw == None):
        flash('Please check your login details and try again.')
        return False
    elif (user["password"] != psw):
        flash('Please check your password.')
        return False

    # if the above check passes, then we know the user has the right credentials
    session['username'] = user["username"].lower()
    return True

