from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash, session
from flask import current_app
import redis
from redis import RedisError
from datetime import datetime
import time
import hashlib
import json
from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import (LoginManager,current_user,login_required,login_user,logout_user,)
from user import requires_access_level, Role
from config import get_db
from common.utils import get_analytics
from utils import pretty_title

analytic = Blueprint('analytic', __name__)

@analytic.route('/analytics')
@login_required
@requires_access_level(Role.ADMIN)
def analytics():
    # 86400000 ms in a day
    # 3600000 ms in an hour
    # wait for RedisTimeSeries support to EMPTY in RedisTimeSeries 1.8
    # then, different charts may be plotted together with a common x axis
    visits_json = get_analytics("keybase:visits".format(id), 86400000, 2592000000)
    authentications_json = get_analytics("keybase:authentications".format(id), 86400000, 2592000000)
    return render_template('analytics.html', visits_json=visits_json, authentications_json=authentications_json)