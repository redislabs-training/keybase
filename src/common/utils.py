import time
import json
import redis
from datetime import datetime
from enum import IntEnum
from flask import redirect, url_for

import shortuuid
from flask import request, Response
from flask_login import current_user
from functools import wraps
import urllib.parse

from src.common.config import REDIS_CFG
import re


def get_db(decode=True):
    try:
        return redis.StrictRedis(host=REDIS_CFG["host"],
                                 port=REDIS_CFG["port"],
                                 password=REDIS_CFG["password"],
                                 db=0,
                                 ssl=REDIS_CFG["ssl"],
                                 ssl_keyfile=REDIS_CFG["ssl_keyfile"],
                                 ssl_certfile=REDIS_CFG["ssl_certfile"],
                                 ssl_ca_certs=REDIS_CFG["ssl_ca_certs"],
                                 ssl_cert_reqs=REDIS_CFG["ssl_cert_reqs"],
                                     decode_responses=decode)
    except redis.exceptions.ConnectionError:
        return redirect(url_for("main_bp.error-page"))


def track_request():
    if current_user.is_authenticated and request.full_path is not None:
        data = {'full_path': request.full_path, 'user': current_user.id}
        get_db().xadd("keybase:requests", data)


def track_errors(e):
    data = {'err': str(e),
            'full_path': request.full_path,
            'agent': request.headers.get('User-Agent')}
    get_db().xadd("keybase:errors", data)


def parse_query_string(q):
    query = urllib.parse.unquote(q).translate(str.maketrans('', '', "\"@!{}()|-=<>[];.'")).strip()
    if len(query) > 0:
        query = "*" + query + "*"
    return query


class ShortUuidPk:
    @staticmethod
    def create_pk() -> str:
        shortuuid.set_alphabet('123456789abcdefghijkmnopqrstuvwxyz')
        return shortuuid.uuid()[:10]


def pretty_title(title):
    return re.sub('[^0-9a-zA-Z]+', '-', title).strip("-").lower()


def get_analytics(timeseries, bucket, duration):
    ts = round(time.time() * 1000)
    ts0 = ts - duration
    data_ts = get_db().ts().range(timeseries, from_time=ts0, to_time=ts, aggregation_type='sum',
                                  bucket_size_msec=bucket)
    data_labels = [datetime.utcfromtimestamp(int(x[0] / 1000)).strftime('%b %d') for x in data_ts]
    data = [x[1] for x in data_ts]
    data_graph = {'labels': data_labels, 'value': data}
    points = json.dumps(data_graph)
    return points


def requires_access_level(access_level):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_allowed(access_level):
                return Response(response="Unauthorized", status=403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


class Role(IntEnum):
    ADMIN = 3
    EDITOR = 2
    VIEWER = 1

    @staticmethod
    def group2role(group):
        if group == 'admin':
            return Role.ADMIN
        elif group == 'editor':
            return Role.EDITOR
        elif group == 'viewer':
            return Role.VIEWER
