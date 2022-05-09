import redis
from redis.commands.search.field import VectorField
from redis.commands.search.query import Query
from redis import RedisError
import numpy as np
import uuid
import urllib.parse
from datetime import datetime
import time
from . import config
from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import login_required, current_user
from flask_simplelogin import login_required

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]

app = Blueprint('app', __name__)

pool = redis.ConnectionPool(host=host, port=port, password=pwd, db=0, decode_responses=True)
conn = redis.Redis(connection_pool=pool)

# Helpers
def isempty(input):
	result = False

	# An argument is considered to be empty if any of the following condition matches
	if str(input) == "None":
		result = True
	
	if str(input) == "":
		result = True
	
	return result

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    search = urllib.parse.unquote(request.args.get('q'))
    rs = conn.ft("document_idx").search(Query(search).paging(0, 10))
    results = []
    for doc in rs.docs:
        results.append({'value': urllib.parse.unquote(doc.name),
                        'label': urllib.parse.unquote(doc.name), 
                        'id': doc.id.split(':')[-1]})
    return jsonify(matching_results=results)

@app.route('/browse', methods=['GET'])
@login_required
def browse():
    TITLE="List documents"
    DESC="Listing documents"

    try:
        #rs = conn.scan_iter(match="keybase:kb:*", count=None, _type="HASH")
        if (request.args.get('q')):
            rs = conn.ft("document_idx").search(Query(request.args.get('q')).return_field("name").return_field("creation").sort_by("creation", asc=False).paging(0, 10))
        else:
            rs = conn.ft("document_idx").search(Query("*").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(0, 10))
        
        if not len(rs.docs):
            return render_template('browse.html', title=TITLE, desc=DESC)
        
        keys = []
        names = []
        creations = []
        for key in rs.docs:
            keys.append(key.id.split(':')[-1])
            names.append(urllib.parse.unquote(key.name))
            creations.append(datetime.utcfromtimestamp(int(key.creation)).strftime('%Y-%m-%d %H:%M:%S'))
        return render_template('browse.html', title=TITLE, desc=DESC, keydocument=zip(keys,names,creations))
    except RedisError as err:
        print(err)
        return render_template('browse.html', title=TITLE, desc=DESC, error=err)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=session['username'])

@app.route('/save', methods=['GET'])
@login_required
def save():
    TITLE="Read Document"
    DESC="Read Document"
    id = uuid.uuid1()
    unixtime = int(time.time())
    timestring = datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S")
    doc = {"content":urllib.parse.unquote(request.args.get('content')), 
            "name":urllib.parse.unquote(request.args.get('name')),
            "creation":unixtime,
            "update":unixtime}
    conn.hmset("keybase:kb:{}".format(id), doc)
    #return render_template('edit.html', title=TITLE, desc=DESC, id=id, name=request.args.get('name'), content=request.args.get('content'))
    return jsonify(message="Document created", id=id)
    #return redirect(url_for('app.edit', id=id))

@app.route('/update', methods=['GET'])
@login_required
def update():
    # Make sure the request.args.get('id') exists, otherwise do not update
    unixtime = int(time.time())

    doc = { "content":urllib.parse.unquote(request.args.get('content')), 
            "name":urllib.parse.unquote(request.args.get('name')),
            "update": unixtime}
    conn.hmset("keybase:kb:{}".format(request.args.get('id')), doc)
    return jsonify(message="Document updated")

@app.route('/load', methods=['GET'])
@login_required
def load():
    imageId = request.args.get('id')
    bytes = conn.get(session['username']+":image:"+imageId)
    return bytes

@app.route('/about', methods=['GET'])
@login_required
def about():
    TITLE="About keybase"
    DESC="About keybase"
    return render_template('about.html', title=TITLE, desc=DESC)

@app.route('/edit', methods=['GET'])
@login_required
def edit():
    id = request.args.get('id')
    TITLE="Read Document"
    DESC="Read Document"
    #if id is None:
    document = conn.hgetall("keybase:kb:{}".format(id))
    document['name'] = urllib.parse.quote(document['name'])
    document['content'] = urllib.parse.quote(document['content'])
    return render_template('edit.html', title=TITLE, desc=DESC, id=id, name=document['name'], content=document['content'])

@app.route('/delete', methods=['GET'])
@login_required
def delete():
    id = request.args.get('id')
    conn.delete("keybase:kb:{}".format(id))
    return redirect(url_for('app.browse'))

@app.route('/view', methods=['GET'])
@login_required
def view():
    id = request.args.get('id')
    TITLE="Read Document"
    DESC="Read Document"
    #if id is None:
    document = conn.hmget("keybase:kb:{}".format(id), ['name', 'content'])
    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])
    return render_template('view.html', title=TITLE,id=id, desc=DESC, document=document)

@app.route('/new')
@login_required
def new():
    TITLE="New Document"
    DESC="New Document"
    return render_template('new.html', title=TITLE, desc=DESC)