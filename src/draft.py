from flask import Blueprint, render_template, redirect, url_for
from redis.commands.search.query import Query
from flask import request
from flask import flash, session
from flask import current_app
import uuid
import urllib.parse
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

draft = Blueprint('draft', __name__)


@draft.route('/drafts')
@login_required
@requires_access_level(Role.EDITOR)
def drafts():
    keys = []
    names = []
    owner = []
    updates = []
    drafts = None

    # Search for own drafts if not admin
    if not current_user.is_admin():
        rs = get_db().ft("document_idx").search(Query('@state:{draft} @owner:('+current_user.id+')').return_field("name").return_field("update").return_field("owner").sort_by("update", asc=False))
        if len(rs.docs): 
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.name))
                owner.append(get_db().hget("keybase:okta:{}".format(key.owner), "name"))
                updates.append(datetime.utcfromtimestamp(int(key.update)).strftime('%Y-%m-%d %H:%M:%S'))
            drafts=zip(keys,names,owner,updates)
    else:
    # And if you are admin, everybody else's drafts
        rs = get_db().ft("document_idx").search(Query('@state:{draft}').return_field("name").return_field("update").return_field("owner").sort_by("update", asc=False))
        if len(rs.docs): 
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.name))
                owner.append(get_db().hget("keybase:okta:{}".format(key.owner), "name"))
                updates.append(datetime.utcfromtimestamp(int(key.update)).strftime('%Y-%m-%d %H:%M:%S'))
            drafts=zip(keys,names,owner,updates)
    
    return render_template("draft.html", drafts=drafts)