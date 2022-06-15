from redis.commands.search.field import VectorField
from redis.commands.search.query import Query
from redis import RedisError
import numpy as np
import uuid
import urllib.parse
from datetime import datetime
import time
from . import config
import json
import threading
import flask
import math
from flask import Response, stream_with_context
from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import (LoginManager,current_user,login_required,login_user,logout_user,)
from sentence_transformers import SentenceTransformer
from user import requires_access_level, Role
from config import get_db
from flask_paginate import Pagination, get_page_args


app = Blueprint('app', __name__)


@app.route('/autocomplete', methods=['GET'])
@login_required
def autocomplete():
    rs = get_db().ft("document_idx").search(Query(urllib.parse.unquote(request.args.get('q')) + " -@state:{draft}").return_field("name").sort_by("creation", asc=False).paging(0, 10))
    results = []

    for doc in rs.docs:
        results.append({'value': urllib.parse.unquote(doc.name),
                        'label': urllib.parse.unquote(doc.name), 
                        'id': doc.id.split(':')[-1]})

    return jsonify(matching_results=results)


def bg_embedding_vector(key):
    content = get_db().hget("keybase:kb:{}".format(key), "content")
    print("Computing vector embedding for " + key)
    model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')
    embedding = model.encode(content).astype(np.float32).tobytes()
    get_db().hset("keybase:kb:{}".format(key), "content_embedding", embedding)
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
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(Query(request.args.get('q') + " -@state:{draft}").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(offset, per_page))
            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma', bulma_style='small', prev_label='Previous', next_label='Next page')
        else: 
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(Query("-@state:{draft}").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(offset, per_page))
            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma', bulma_style='small', prev_label='Previous', next_label='Next page')
            print(rs)

        if len(rs.docs): 
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.name))
                creations.append(datetime.utcfromtimestamp(int(key.creation)).strftime('%Y-%m-%d %H:%M:%S'))
            keydocument=zip(keys,names,creations)

        return render_template('browse.html', title=TITLE, desc=DESC, keydocument=keydocument, page=page, per_page=per_page, pagination=pagination)
    except RedisError as err:
        print(err)
        return render_template('browse.html', title=TITLE, desc=DESC, error=err)

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('app.browse'))


@app.route('/save', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def save():
    id = uuid.uuid1()
    unixtime = int(time.time())
    timestring = datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S")

    doc = {"content":urllib.parse.unquote(request.form['content']), 
            "name":urllib.parse.unquote(request.form['name']),
            "creation":unixtime,
            "state":"draft",
            "author":current_user.id,
            "owner":current_user.id,
            "processable":0,
            "update":unixtime}
    get_db().hmset("keybase:kb:{}".format(id), doc)
    return jsonify(message="Document created", id=id)


@app.route('/publish', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def publish():
    # Make sure the request.form['id'] exists, otherwise do not publish
    if not get_db().exists("keybase:kb:{}".format(request.form['id'])):
        return jsonify(message="Error publishing the document")

    unixtime = int(time.time())

    # First, save the document and change the state TAG to "public"
    doc = { "content":urllib.parse.unquote(request.form['content']),
            "name":urllib.parse.unquote(request.form['name']),
            "state":"public",
            "processable":1,
            "update": unixtime}
    get_db().hmset("keybase:kb:{}".format(request.form['id']), doc)
    return jsonify(message="Document published")


@app.route('/update', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def update():
    # Make sure the request.form['id'] exists, otherwise do not save
    if not get_db().exists("keybase:kb:{}".format(request.form['id'])):
        return jsonify(message="Error saving the document")

    unixtime = int(time.time())

    doc = { "content":urllib.parse.unquote(request.form['content']),
            "name":urllib.parse.unquote(request.form['name']),
            "state":"draft",
            "owner":current_user.id,
            "processable":0,
            "update": unixtime}
    get_db().hmset("keybase:kb:{}".format(request.form['id']), doc)

    return jsonify(message="Document saved among drafts")

@app.route('/about', methods=['GET'])
@login_required
def about():
    TITLE="About keybase"
    DESC="About keybase"
    return render_template('about.html', title=TITLE, desc=DESC)

@app.route('/edit', methods=['GET'])
@login_required
@requires_access_level(Role.EDITOR)
def edit():
    id = request.args.get('id')
    TITLE="Read Document"
    DESC="Read Document"
    #if id is None:
    document = get_db().hmget("keybase:kb:{}".format(id), ['name', 'content', 'state'])
    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])
    return render_template('edit.html', title=TITLE, desc=DESC, id=id, name=document[0], content=document[1], state=document[2])

@app.route('/delete', methods=['GET'])
@login_required
@requires_access_level(Role.ADMIN)
def delete():
    id = request.args.get('id')
    get_db().delete("keybase:kb:{}".format(id))
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

    bookmarked = get_db().hexists("keybase:bookmark:{}".format(current_user.id), id)

    document = get_db().hmget("keybase:kb:{}".format(request.args.get('id')), ['name', 'content', 'state', 'owner'])
    
    if document[0] == None:
        return redirect(url_for('app.browse'))

    # If it is a draft, role is editor: make sure the editor owns the draft. Editor can edit the draft
    # If it is a draft, role is admin: can see, edit and publish
    if (document[2] == 'draft' and document[3]!=current_user.id and not current_user.is_admin()):
        print("This document is locked for editing, if not an admin, cannot read it")
        return render_template('locked.html', name=document[0])

    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])

    # Fetch recommendations using LUA and avoid sending vector embeddings back an forth
    #luascript = conn.register_script("local vector = redis.call('hmget',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','document_idx','*=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres")
    #pipe = conn.pipeline()
    #luascript(keys=["keybase:kb:{}".format(request.args.get('id'))], client=pipe)
    #r = pipe.execute()

    # The first element in the returned list is the number of keys returned, start iterator from [1:]
    # Then, iterate the results in pairs, because they key name is alternated with the returned fields
    #it = iter(r[0][1:])
    #for x in it:
    #    keys.append(str(x.split(':')[-1]))
    #    names.append(str(next(it)[3]))
        #print (x.split(':')[-1], next(it)[3])
    #suggestlist=zip(keys, names)

    # Fetch recommendations using LUA and avoid sending vector embeddings back an forth
    # The first element in the returned list is the number of keys returned, start iterator from [1:]
    # Then, iterate the results in pairs, because they key name is alternated with the returned fields

    if get_db().hexists("keybase:kb:{}".format(request.args.get('id')), 'content_embedding'):
        keys_and_args = ["keybase:kb:{}".format(request.args.get('id'))]
        res = get_db().eval("local vector = redis.call('hmget',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','document_idx','*=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres", 1, *keys_and_args)
        it = iter(res[1:])
        for x in it:
            keys.append(str(x.split(':')[-1]))
            names.append(str(next(it)[3]))
            #print (x.split(':')[-1], next(it)[3])
        suggestlist=zip(keys, names)


    """
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
    """
    return render_template('view.html', title=TITLE, desc=DESC, docid=id, bookmarked=bookmarked, document=document, suggestlist=suggestlist)

@app.route('/new')
@login_required
@requires_access_level(Role.EDITOR)
def new():
    TITLE="New Document"
    DESC="New Document"
    return render_template('new.html', title=TITLE, desc=DESC)