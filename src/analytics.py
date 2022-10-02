from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash, session
from flask import current_app
import redis
from redis import RedisError
from . import config
from datetime import datetime
import time
import hashlib
import json
from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import (LoginManager,current_user,login_required,login_user,logout_user,)
from user import requires_access_level, Role
from config import get_db
from utils import pretty_title

analytic = Blueprint('analytic', __name__)

@analytic.route('/analytics')
@login_required
@requires_access_level(Role.ADMIN)
def analytics():
    bucket = 86400000
    duration = 2592000000
    ts = round(time.time() * 1000)
    ts0 = ts - 2592000000

    # 86400000 ms in a day
    # 3600000 ms in an hour
    visits_ts = get_db().ts().range("keybase:visits", from_time=ts0, to_time=ts, aggregation_type='sum', bucket_size_msec=bucket)
    visits_labels = [datetime.utcfromtimestamp(int(x[0]/1000)).strftime('%b %d') for x in visits_ts]
    visits = [x[1] for x in visits_ts]
    visits_graph = {}
    visits_graph['labels'] = visits_labels
    visits_graph['value'] = visits
    visits_json = json.dumps(visits_graph)

    # wait for RedisTimeSeries support to EMPTY in RedisTimeSeries 1.8
    # then, different charts may be plotted together with a common x axis
    authentications_ts = get_db().ts().range("keybase:authentications", from_time=ts0, to_time=ts, aggregation_type='sum', bucket_size_msec=bucket)
    authentication_labels = [datetime.utcfromtimestamp(int(x[0]/1000)).strftime('%b %d') for x in authentications_ts]
    authentications = [x[1] for x in authentications_ts]
    authentications_graph = {}
    authentications_graph['labels'] = authentication_labels
    authentications_graph['value'] = authentications
    authentications_json = json.dumps(authentications_graph)
    
    return render_template('analytics.html', visits_json=visits_json, authentications_json=authentications_json)


@analytic.route('/visits')
@login_required
@requires_access_level(Role.ADMIN)
def visits():
    ts = round(time.time() * 1000)
    ts0 = ts - 2592000000
    visits = get_db().ts().range("keybase:visits", 
                                from_time=ts0, 
                                to_time=ts,
                                aggregation_type='sum',
                                bucket_size_msec=86400000)
    print(visits)
    return jsonify(matching_results=visits)