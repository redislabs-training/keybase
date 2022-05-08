from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash
from flask import jsonify
import redis
from . import config

api = Blueprint('api', __name__)

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]
redis = redis.Redis(host=host, port=port, password=pwd, charset="utf-8", decode_responses=True)

@api.route('/api/<string:username>')
def userposts(username):
    keys = []
    rs = redis.scan_iter(match=username+":image*", count=None, _type="STRING")
    for key in rs:
        keys.append(key.split(':')[-1])
    return jsonify(matching_results=keys)
