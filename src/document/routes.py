from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import (current_user, login_required)
from flask_paginate import Pagination, get_page_args
from redis import RedisError
from datetime import datetime
import time
import urllib.parse
from redis.commands.search.query import Query
import shortuuid

from src.user import requires_access_level, Role
from src.common.config import get_db
from src.common.utils import get_analytics, pretty_title


document_bp = Blueprint('document_bp', __name__,
                        template_folder='./templates')

@document_bp.before_request
def before_request():
    # Store visits in a time series visited pages
    if current_user.is_authenticated and request.endpoint == "document_bp.doc":
        get_db().ts().add("keybase:visits", "*", 1, duplicate_policy='first')


@document_bp.route('/autocomplete', methods=['GET'])
@login_required
def autocomplete():
    # Sanitize input for RediSearch
    query = urllib.parse.unquote(request.args.get('q')).translate(str.maketrans('','',"\"@!{}()|-=>"))
    rs = get_db().ft("document_idx").search(Query(query + " -@state:{draft}").return_field("name").sort_by("creation", asc=False).paging(0, 10))
    results = []

    for doc in rs.docs:
        results.append({'value': urllib.parse.unquote(doc.name),
                        'label': urllib.parse.unquote(doc.name),
                        'pretty': pretty_title(urllib.parse.unquote(doc.name)),
                        'id': doc.id.split(':')[-1]})

    return jsonify(matching_results=results)


@document_bp.route('/browse', methods=['GET'])
@login_required
def browse():
    TITLE="List documents"
    DESC="Listing documents"
    keys = []
    names = []
    pretty = []
    creations = []
    keydocument = None
    pagination = None
    rs = None

    try:
        if (request.args.get('q')):
            # Sanitized input for RediSearch
            query = urllib.parse.unquote(request.args.get('q')).translate(str.maketrans('','',"\"@!{}()|-=>"))
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(Query(query + " -@state:{draft}").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(offset, per_page))
            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma', bulma_style='small', prev_label='Previous', next_label='Next page')
        elif (request.args.get('tag')):
            # Sanitized tags for RediSearch: may be empty afterwards, a search like @tags:{""} fails
            tag = request.args.get('tag').translate(str.maketrans('','',"\"@!{}()|-=>"))
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            if len(tag):
                rs = get_db().ft("document_idx").search(Query("@tags:{"+tag+"} -@state:{draft}").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(offset, per_page))
                pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma', bulma_style='small', prev_label='Previous', next_label='Next page')
        else:
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(Query("-@state:{draft}").return_field("name").return_field("creation").sort_by("creation", asc=False).paging(offset, per_page))
            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma', bulma_style='small', prev_label='Previous', next_label='Next page')

        # If after sanitizing the input there is nothing to show, redirect to main
        if (rs != None) and len(rs.docs):
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.name))
                pretty.append(pretty_title(urllib.parse.unquote(key.name)))
                creations.append(datetime.utcfromtimestamp(int(key.creation)).strftime('%Y-%m-%d'))
            keydocument=zip(keys,names,pretty,creations)

        return render_template('browse.html', title=TITLE, desc=DESC, keydocument=keydocument, page=page, per_page=per_page, pagination=pagination)
    except RedisError as err:
        print(err)
        return redirect(url_for("document_bp.browse"))


@document_bp.route('/save', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def save():
    shortuuid.set_alphabet("123456789abcdefghijkmnopqrstuvwxyz")
    id = shortuuid.uuid()[:10]
    unixtime = int(time.time())
    timestring = datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S")

    doc = {"content": urllib.parse.unquote(request.form['content']),
           "name": urllib.parse.unquote(request.form['name']),
           "creation": unixtime,
           "state": "draft",
           "author": current_user.id,
           "owner": current_user.id,
           "processable": 0,
           "update": unixtime}
    get_db().hmset("keybase:kb:{}".format(id), doc)
    return jsonify(message="Document created", id=id)


@document_bp.route('/publish', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def publish():
    # Make sure the request.form['id'] exists, otherwise do not publish
    if not get_db().exists("keybase:kb:{}".format(request.form['id'])):
        return jsonify(message="Error publishing the document")

    unixtime = int(time.time())

    # First, save the document and change the state TAG to "public"
    doc = {"content": urllib.parse.unquote(request.form['content']),
           "name": urllib.parse.unquote(request.form['name']),
           "state": "public",
           "processable": 1,
           "update": unixtime}
    get_db().hmset("keybase:kb:{}".format(request.form['id']), doc)
    return jsonify(message="Document published")


@document_bp.route('/addtag', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def addtag():
    taglist = []

    # Make sure the tag exists and is valid
    if not get_db().hexists("keybase:tags", request.form['tag']):
        return jsonify(message="The tag does not exist", code="error")

    # Get tags for this document
    tags = get_db().hget("keybase:kb:{}".format(request.form['id']), "tags")
    if (tags != None) and (len(tags) > 0):
        taglist = tags.split(',')

    #  The document hasn't the tag, and it can be added
    if not taglist.count(request.form['tag']) > 0:
        taglist.append(request.form['tag'])
        get_db().hset("keybase:kb:{}".format(request.form['id']), "tags", ",".join(taglist))
        print(",".join(taglist))
    else:
        return jsonify(message="Document already tagged", code="warn")

    return jsonify(message="The tag has been added", code="success")


@document_bp.route('/deltag', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def deltag():
    taglist = []

    # Get tags for this document
    tags = get_db().hget("keybase:kb:{}".format(request.form['id']), "tags")
    if tags != None:
        taglist = tags.split(',')
        taglist.remove(request.form['tag'])
        get_db().hset("keybase:kb:{}".format(request.form['id']), "tags", ",".join(taglist))

    return jsonify(message="The tag has been removed", code="success", tags=taglist)


@document_bp.route('/update', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def update():
    # Make sure the request.form['id'] exists, otherwise do not save
    if not get_db().exists("keybase:kb:{}".format(request.form['id'])):
        return jsonify(message="Error saving the document")

    unixtime = int(time.time())

    doc = {"content": urllib.parse.unquote(request.form['content']),
           "name": urllib.parse.unquote(request.form['name']),
           "state": "draft",
           "owner": current_user.id,
           "processable": 0,
           "update": unixtime}
    get_db().hmset("keybase:kb:{}".format(request.form['id']), doc)

    return jsonify(message="Document saved as draft")


@document_bp.route('/edit/<id>')
@login_required
@requires_access_level(Role.EDITOR)
def edit(id):
    TITLE = "Read Document"
    DESC = "Read Document"
    # if id is None:
    document = get_db().hmget("keybase:kb:{}".format(id), ['name', 'content', 'state', 'tags'])

    # Verify that there is a document associated to the id
    if document[0] == None:
        return redirect(url_for('document_bp.browse'))

    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])
    return render_template('edit.html', title=TITLE, desc=DESC, id=id, name=document[0],
                           pretty=pretty_title(urllib.parse.unquote(document[0])), content=document[1],
                           state=document[2], tags=document[3])


@document_bp.route('/delete/<id>')
@login_required
@requires_access_level(Role.ADMIN)
def delete(id):
    # id = request.args.get('id')
    get_db().delete("keybase:kb:{}".format(id))
    return redirect(url_for('document_bp.browse'))


@document_bp.route('/doc/<id>', defaults={'prettyurl': None})
@document_bp.route('/doc/<id>/<prettyurl>')
@login_required
def doc(id, prettyurl):
    TITLE = "Read Document"
    DESC = "Read Document"
    keys = []
    names = []
    pretty = []
    suggestlist = None

    bookmarked = get_db().hexists("keybase:bookmark:{}".format(current_user.id), id)
    document = get_db().hmget("keybase:kb:{}".format(id), ['name', 'content', 'state', 'owner', 'tags'])

    if document[0] == None:
        return redirect(url_for('document_bp.browse'))

    # If it is a draft, role is editor: make sure the editor owns the draft. Editor can edit the draft
    # If it is a draft, role is admin: can see, edit and publish
    if (document[2] == 'draft' and document[3] != current_user.id and not current_user.is_admin()):
        print("This document is locked for editing, if not an admin, cannot read it")
        return render_template('locked.html', name=document[0])

    document[0] = urllib.parse.quote(document[0])
    document[1] = urllib.parse.quote(document[1])

    # The document can be rendered, count the visit
    get_db().ts().add("keybase:docview:{}".format(id), "*", 1, duplicate_policy='first')

    # Only the admin can see document visits
    analytics = None
    if current_user.is_admin():
        analytics = get_analytics("keybase:docview:{}".format(id), 86400000, 2592000000)

    #  Fetch recommendations using LUA and avoid sending vector embeddings back an forth
    # luascript = conn.register_script("local vector = redis.call('hmget',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','document_idx','*=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres")
    # pipe = conn.pipeline()
    # luascript(keys=["keybase:kb:{}".format(request.args.get('id'))], client=pipe)
    # r = pipe.execute()

    #  The first element in the returned list is the number of keys returned, start iterator from [1:]
    # Then, iterate the results in pairs, because they key name is alternated with the returned fields
    # it = iter(r[0][1:])
    # for x in it:
    #    keys.append(str(x.split(':')[-1]))
    #    names.append(str(next(it)[3]))
    # print (x.split(':')[-1], next(it)[3])
    # suggestlist=zip(keys, names)

    #  Fetch recommendations using LUA and avoid sending vector embeddings back an forth
    #  The first element in the returned list is the number of keys returned, start iterator from [1:]
    # Then, iterate the results in pairs, because they key name is alternated with the returned fields

    if get_db().hexists("keybase:kb:{}".format(id), 'content_embedding'):
        keys_and_args = ["keybase:kb:{}".format(id)]
        res = get_db().eval(
            "local vector = redis.call('hmget',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','document_idx','*=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres",
            1, *keys_and_args)
        it = iter(res[1:])
        for x in it:
            keys.append(str(x.split(':')[-1]))
            docName = str(next(it)[3])
            names.append(docName)
            pretty.append(pretty_title(docName))
            # print (x.split(':')[-1], next(it)[3])
        suggestlist = zip(keys, names, pretty)

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
    return render_template('view.html', title=TITLE, desc=DESC, docid=id, bookmarked=bookmarked, document=document,
                           suggestlist=suggestlist, analytics=analytics)
