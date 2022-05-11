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
import threading
import flask
from flask import Response, stream_with_context
from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import login_required, current_user
from flask_simplelogin import login_required
from sentence_transformers import SentenceTransformer

# Database Connection
host = config.REDIS_CFG["host"]
port = config.REDIS_CFG["port"]
pwd = config.REDIS_CFG["password"]

app = Blueprint('app', __name__)

pool = redis.ConnectionPool(host=host, port=port, password=pwd, db=0, decode_responses=False)
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


def bg_embedding_vector(key):
    content = conn.hget("keybase:kb:{}".format(key), "content")
    print("Computing vector embedding for " + key)
    model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')
    embedding = model.encode(content.decode('utf-8')).astype(np.float32).tobytes()
    conn.hset("keybase:kb:{}".format(key), "content_embedding", embedding)
    print("Done vector embedding for " + key)

@app.route('/browse', methods=['GET'])
@login_required
def browse():
    TITLE="List documents"
    DESC="Listing documents"
    keys = []
    names = []
    creations = []
    keydocument = None

    # Clear all the flashed messages
    flask.get_flashed_messages()

    try:
        if (request.args.get('q')):
            rs = conn.ft("document_idx").search(Query(request.args.get('q')).return_field("name").return_field("creation").sort_by("creation", asc=False).paging(0, 10))
        else:
            rs = conn.ft("document_idx").search(Query("*").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(0, 10))
        
        if len(rs.docs): 
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.name))
                creations.append(datetime.utcfromtimestamp(int(key.creation)).strftime('%Y-%m-%d %H:%M:%S'))
            keydocument=zip(keys,names,creations)
        return render_template('browse.html', title=TITLE, desc=DESC, keydocument=keydocument)
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

    # Update the vector embedding in the background
    sscanThread = threading.Thread(target=bg_embedding_vector, args=(str(id),)) 
    sscanThread.daemon = True
    sscanThread.start()

    return jsonify(message="Document created", id=id)


@app.route('/update', methods=['GET'])
@login_required
def update():
    # Make sure the request.args.get('id') exists, otherwise do not update
    unixtime = int(time.time())

    doc = { "content":urllib.parse.unquote(request.args.get('content')),
            "name":urllib.parse.unquote(request.args.get('name')),
            "update": unixtime}
    conn.hmset("keybase:kb:{}".format(request.args.get('id')), doc)

    # Update the vector embedding in the background
    sscanThread = threading.Thread(target=bg_embedding_vector, args=(request.args.get('id'),)) 
    sscanThread.daemon = True
    sscanThread.start()

    return jsonify(message="Document updated")

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
    document = conn.hmget("keybase:kb:{}".format(id), ['name', 'content'])
    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])
    return render_template('edit.html', title=TITLE, desc=DESC, id=id, name=document[0], content=document[1])

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
    keys = []
    names = []
    suggestlist = None
    #if id is None:

    document = conn.hmget("keybase:kb:{}".format(request.args.get('id')), ['name', 'content', 'content_embedding'])
    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])

    # Fetching suggestions only if the vector embedding is available
    if (document[2] != None):
        q = Query("*=>[KNN 6 @content_embedding $vec]").sort_by("__content_embedding_score")
        res = conn.ft("document_idx").search(q, query_params={"vec": document[2]})
        for doc in res.docs:
            if (doc.id.split(':')[-1] == request.args.get('id')):
                continue
            suggestionid = doc.id.split(':')[-1]
            suggest = conn.hmget("keybase:kb:{}".format(suggestionid), ['name'])
            keys.append(suggestionid)
            names.append(suggest[0].decode('utf-8'))
        suggestlist=zip(keys, names)

    return render_template('view.html', title=TITLE,id=request.args.get('id'), desc=DESC, document=document, suggestlist=suggestlist)

@app.route('/new')
@login_required
def new():
    TITLE="New Document"
    DESC="New Document"
    return render_template('new.html', title=TITLE, desc=DESC)