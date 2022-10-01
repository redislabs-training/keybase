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
    ts = round(time.time() * 1000)
    ts0 = ts - 2592000000

    # 86400000 ms in a day
    # 3600000 ms in an hour
    visits_ts = get_db().ts().range("keybase:visits", from_time=ts0, to_time=ts, aggregation_type='sum', bucket_size_msec=86400000)
    authentications_ts = get_db().ts().range("keybase:authentications", from_time=ts0, to_time=ts, aggregation_type='sum', bucket_size_msec=86400000)

    labels = [datetime.utcfromtimestamp(int(x[0]/1000)).strftime('%b %d') for x in visits_ts]
    visits = [x[1] for x in visits_ts]
    authentications = [x[1] for x in authentications_ts]
    graph = {}
    graph['labels'] = labels
    graph['visits'] = visits

    # wait for RedisTimeSeries support to EMPTY: empty buckets are not plotted:
    # if there are samples in a bucket for visits but not for auth, auth will not be reported 
    # as zero, but skipped, which makes plotting together different charts incorrect.
    # Uncomment when RedisTimeSeries 1.8 is out
    # graph['authentications'] = authentications
    json_data = json.dumps(graph)
    return render_template('analytics.html', json_data=json_data)


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