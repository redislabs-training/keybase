from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import (LoginManager,current_user,login_required,login_user,logout_user,)

from src.user import requires_access_level, Role
from src.common.utils import get_analytics

analytics_bp = Blueprint('analytics_bp', __name__,
                        template_folder='./templates')

@analytics_bp.route('/analytics')
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