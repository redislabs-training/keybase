import flask
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import (current_user, login_required)
from flask_paginate import Pagination, get_page_args
from redis import RedisError
from datetime import datetime
import time, urllib.parse, json
from redis.commands.search.query import Query
from .document import Document, Version, CurrentVersion
from pydantic import ValidationError
from redis_om import NotFoundError

from src.common.utils import get_db, parse_query_string, get_analytics, pretty_title, track_request, requires_access_level, Role

document_bp = Blueprint('document_bp', __name__,
                        template_folder='./templates')


@document_bp.before_request
def before_request():
    # Track the request in a Redis Stream
    track_request()

    # Store visits in a time series visited pages
    if current_user.is_authenticated and request.endpoint == "document_bp.doc":
        get_db().ts().add("keybase:visits", "*", 1, duplicate_policy='first')


@document_bp.route('/autocomplete', methods=['GET'])
@login_required
def autocomplete():
    # Sanitize input for RediSearch
    query = parse_query_string(flask.request.args.get('q'))
    query = "@currentversion_name_fts|currentversion_content_fts:'" + query + "'"
    rs = get_db().ft("document_idx")\
            .search(Query(query + " @state:{published|review}")
            .return_field("currentversion_name")
            .sort_by("creation", asc=False)
            .paging(0, 10))

    results = []

    for doc in rs.docs:
        results.append({'value': urllib.parse.unquote(doc.currentversion_name),
                        'label': urllib.parse.unquote(doc.currentversion_name),
                        'pretty': pretty_title(urllib.parse.unquote(doc.currentversion_name)),
                        'id': doc.id.split(':')[-1]})

    return jsonify(matching_results=results)


@document_bp.route('/browse', methods=['GET', 'POST'])
@login_required
def browse():
    TITLE = "List documents"
    DESC = "Listing documents"
    keys = []
    names = []
    pretty = []
    creations = []
    keydocument = None
    pagination = None
    rs = None
    category = ""
    asc = 0

    try:
        if flask.request.method == 'GET':
            catfilter, tagfilter, queryfilter, prvfilter, sortbyfilter = "", "", "", "", False

            # Check the ordering
            if flask.request.args.get('asc') == "true":
                sortbyfilter = True
                asc = 1

            # Sanitized input for RediSearch
            if flask.request.args.get('q'):
                queryfilter = parse_query_string(flask.request.args.get('q'))
                queryfilter = "@currentversion_name_fts|currentversion_content_fts:'" + queryfilter + "'"
            # If the category is good, can be processed and set in the UI
            if flask.request.args.get('cat'):
                if get_db().hexists("keybase:categories", flask.request.args.get('cat')):
                    catfilter = " @category:{"+flask.request.args.get('cat')+"} "
                    category = flask.request.args.get('cat')

            # Sanitized tags for RediSearch: may be empty afterwards, a search like @tags:{""} fails
            if flask.request.args.get('tag'):
                tag = flask.request.args.get('tag').translate(str.maketrans('', '', "\"@!{}()|-=>"))
                tagfilter = " @tags:{" + tag + "} "

            prv = flask.request.args.get('prv')
            if prv and (prv=='internal' or prv=='public'):
                prvfilter = " @privacy:{" + prv + "} "

            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(
                Query(queryfilter + catfilter + tagfilter + prvfilter + " @state:{published|review}")
                .return_field("currentversion_name")
                .return_field("creation")
                .sort_by("creation", asc=sortbyfilter)
                .paging(offset, per_page))

            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                                    bulma_style='small', prev_label='Previous', next_label='Next page')

        # If after sanitizing the input there is nothing to show, redirect to main
        if (rs is not None) and len(rs.docs):
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.currentversion_name))
                pretty.append(pretty_title(urllib.parse.unquote(key.currentversion_name)))
                creations.append(datetime.utcfromtimestamp(int(key.creation)).strftime('%Y-%m-%d'))
            keydocument = zip(keys, names, pretty, creations)

        # Get the categories
        categories = get_db().hgetall("keybase:categories")
        return render_template('browse.html', title=TITLE, desc=DESC, categories=categories, keydocument=keydocument, page=page,
                               per_page=per_page, pagination=pagination, category=category, asc=asc, privacy=prv)
    except RedisError as err:
        print(err)
        return redirect(url_for("document_bp.browse"))


@document_bp.route('/save', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def save():
    unixtime = int(time.time())

    try:
        currentversion = CurrentVersion(
            name=urllib.parse.unquote(request.form['name']),
            content=urllib.parse.unquote(request.form['content']),
            last=unixtime,
            owner=current_user.id
        )

        editorversion = Version(
            name=urllib.parse.unquote(request.form['name']),
            content=urllib.parse.unquote(request.form['content']),
            last=unixtime,
            owner=current_user.id
        )

        doc = Document(
            editorversion=editorversion,
            currentversion=currentversion,
            description="",
            keyword="",
            tags="",
            creation=unixtime,
            updated=unixtime,
            processable=0,
            author=current_user.id,
            versions=[]
        )

        doc.save()
    except ValidationError as e:
        print(e)

    return jsonify(message="Document created", id=doc.pk)


@document_bp.route('/publish', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def publish():
    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="Error publishing the document"), 404

    if document.state == "published":
        return jsonify(message="Document already published"), 403

    unixtime = int(time.time())

    version = Version(
        name=urllib.parse.unquote(request.form['name']),
        content=urllib.parse.unquote(request.form['content']),
        last=unixtime,
        owner=document.editorversion.owner
    )

    currentversion = CurrentVersion(
        name=urllib.parse.unquote(request.form['name']),
        content=urllib.parse.unquote(request.form['content']),
        last=unixtime,
        owner=document.editorversion.owner
    )

    document.versions.insert(0, version)

    # Save the document and change the state TAG to "published"
    document.editorversion = version
    document.currentversion = currentversion
    document.state = "published"
    document.processable = 1
    document.updated = unixtime
    document.save()

    return jsonify(message="Document published")


@document_bp.route('/addmetadata', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def addmetadata():
    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="The document does not exist", code="error"),404

    if len(request.form['keyword']) > 160:
        return jsonify(message="Keywords too long: max is 160 chars", code="error"), 500

    if len(request.form['description']) > 160:
        return jsonify(message="Description too long: max is 160 chars", code="error"), 500

    document.keyword = request.form['keyword']
    document.description = request.form['description']
    document.save()
    return jsonify(message="The metadata has been saved", code="success"),200


@document_bp.route('/addtag', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def addtag():
    taglist = []

    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="The document does not exist", code="error"),404

    # Make sure the tag exists and is valid
    if not get_db().hexists("keybase:tags", request.form['tag']):
        return jsonify(message="The tag does not exist", code="error")

    # Get tags for this document
    if (document.tags is not None) and (len(document.tags) > 0):
        taglist = document.tags.split('|')

    # The document hasn't the tag, and it can be added
    if not taglist.count(request.form['tag']) > 0:
        taglist.append(request.form['tag'])
        document.tags = "|".join(taglist)
        document.save()
    else:
        return jsonify(message="Document already tagged", code="warn")

    return jsonify(message="The tag has been added", code="success", tags=taglist)


@document_bp.route('/addcategory', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def addcategory():
    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="The document does not exist", code="error"),404

    # Make sure the category exists
    if not get_db().hexists("keybase:categories", request.form['cat']) and len(request.form['cat']):
        return jsonify(message="The category does not exist", code="error")

    document.category = request.form['cat']
    document.save()
    return jsonify(message="The category has been changed", code="success")

@document_bp.route('/setprivacy', methods=['POST'])
@login_required
@requires_access_level(Role.ADMIN)
def setprivacy():
    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="The document does not exist", code="error"),404

    # Make sure the privacy is correct
    if not (request.form['privacy'] == 'internal') and not (request.form['privacy'] == 'public'):
        return jsonify(message="The privacy setting not exist", code="error"),500

    # Do not recommend
    privacy = { "privacy" : request.form['privacy']}
    get_db().hset("keybase:vss:{}".format(request.form['id']), mapping=privacy)

    document.privacy = request.form['privacy']
    document.save()
    return jsonify(message="The privacy has been changed", code="success")


@document_bp.route('/deltag', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def deltag():
    taglist = []

    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="The document does not exist", code="error"),404

    # Get tags for this document
    if (document.tags is not None) and (len(document.tags) > 0):
        taglist = document.tags.split('|')
        taglist.remove(request.form['tag'])
        document.tags = "|".join(taglist)
        document.save()

    return jsonify(message="The tag has been removed", code="success", tags=taglist)


@document_bp.route('/update', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def update():
    try:
        document = Document.get(request.form['id'])
    except NotFoundError:
        return jsonify(message="Error saving the document"), 404

    unixtime = int(time.time())

    # Save the document, which becomes a current review
    document.editorversion.content = urllib.parse.unquote(request.form['content'])
    document.editorversion.name = urllib.parse.unquote(request.form['name'])
    document.editorversion.last = unixtime
    document.editorversion.owner = current_user.id
    document.state = "review"
    document.save()

    return jsonify(message="Document saved as review")


@document_bp.route('/edit/<id>')
@login_required
@requires_access_level(Role.EDITOR)
def edit(id):
    TITLE = "Edit Document"
    DESC = "Edit Document"

    try:
        document = Document.get(id)
    except NotFoundError:
        return redirect(url_for('document_bp.browse')), 404

    if document.state == 'review' and document.editorversion.owner != current_user.id and not current_user.is_admin():
        return render_template('locked.html', name=document.currentversion.name), 403

    # These are all the categories in the system, for the taxonomy
    # System tags are not returned, now. They can be searched
    categories = get_db().hgetall("keybase:categories")

    document.editorversion.name = urllib.parse.quote(document.editorversion.name)
    document.editorversion.content = urllib.parse.quote(document.editorversion.content)

    return render_template('edit.html',
                           title=TITLE,
                           desc=DESC,
                           document=document,
                           categories=categories,
                           pretty=pretty_title(urllib.parse.unquote(document.editorversion.name)))


@document_bp.route('/delete/<id>')
@login_required
@requires_access_level(Role.ADMIN)
def delete(id):
    try:
        Document.delete(id)
        get_db().delete("keybase:vss:{}".format(id))
    except NotFoundError:
        return redirect(url_for('document_bp.browse')), 404

    return redirect(url_for('document_bp.browse')), 302


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

    try:
        document = Document.get(id)
    except NotFoundError:
        return redirect(url_for('document_bp.browse')), 404

    # Check if the document is bookmarked
    bookmarked = get_db().hexists("keybase:bookmark:{}".format(current_user.id), id)

    # If it is a draft, make sure the user is not a viewer
    if document.state == 'draft' and current_user.is_viewer():
        return render_template('locked.html', name=document.currentversion.name), 403

    # If it is a draft, make sure the user is the author
    # If it is a draft, role is admin: can see, edit and publish
    if document.state == 'draft' and document.author != current_user.id and not current_user.is_admin():
        return render_template('locked.html', name=document.currentversion.name), 403

    document.currentversion.name = urllib.parse.quote(document.currentversion.name)
    document.currentversion.content = urllib.parse.quote(document.currentversion.content)

    # The document can be rendered, count the visit
    get_db().ts().add("keybase:docview:{}".format(id), "*", 1, duplicate_policy='first')

    # Only the admin can see document visits
    analytics = None
    if current_user.is_admin():
        analytics = get_analytics("keybase:docview:{}".format(id), 86400000, 2592000000)

    # Fetch recommendations using LUA and avoid sending vector embeddings back an forth
    # The first element in the returned list is the number of keys returned, start iterator from [1:]
    # Then, iterate the results in pairs, because the key name is alternated with the returned fields

    # With register_script
    # luascript = conn.register_script("local vector = redis.call('hmget',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','document_idx','*=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres")
    # pipe = conn.pipeline()
    # luascript(keys=["keybase:kb:{}".format(request.args.get('id'))], client=pipe)
    # r = pipe.execute()

    if get_db().hexists("keybase:vss:{}".format(id), "content_embedding"):
        keys_and_args = ["keybase:vss:{}".format(id)]
        res = get_db().eval(
            "local vector = redis.call('HMGET',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','vss_idx','@state:{published|review}=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres",
            1, *keys_and_args)

        it = iter(res[1:])
        for x in it:
            keys.append(str(x.split(':')[-1]))
            docName = str(next(it)[3])
            names.append(docName)
            pretty.append(pretty_title(docName))
        suggestlist = zip(keys, names, pretty)

    return render_template('view.html', title=TITLE, desc=DESC, docid=id, bookmarked=bookmarked, document=document,
                           suggestlist=suggestlist, analytics=analytics)


@document_bp.route('/new/<doc>')
@login_required
@requires_access_level(Role.EDITOR)
def new(doc):
    TITLE = "New Document"
    DESC = "New Document"
    template = ""

    if doc == 'case':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Executive Summary \n\n\n<br>\n<br>\n<br>\n## Introduction \n\n\n<br>\n<br>\n<br>\n## Analysis \n\n\n<br>\n<br>\n<br>\n## Alternatives and Decision Criteria \n\n\n<br>\n<br>\n<br>\n## Recommendations and Implementation Plan \n\n\n<br>\n<br>\n<br>\n## Conclusion \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'troubleshooting':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Symptoms \n\n\n<br>\n<br>\n<br>\n## Changes \n\n\n<br>\n<br>\n<br>\n## Cause \n\n\n<br>\n<br>\n<br>\n## Solution \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'design':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Purpose \n\n\n<br>\n<br>\n<br>\n## Scope \n\n\n<br>\n<br>\n<br>\n## Details \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'howto':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Goal \n\n\n<br>\n<br>\n<br>\n## Solution \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'qa':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Question \n\n\n<br>\n<br>\n<br>\n## Answer \n\n\n<br>\n<br>\n<br>\n## References")
    return render_template('new.html', title=TITLE, desc=DESC, template=template)