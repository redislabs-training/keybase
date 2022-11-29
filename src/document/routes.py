from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import (current_user, login_required)
from flask_paginate import Pagination, get_page_args
from redis import RedisError
from datetime import datetime
import time
import urllib.parse
from redis.commands.search.query import Query
from .document import Document, Version
from pydantic import ValidationError
from redis_om import NotFoundError

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
    query = urllib.parse.unquote(request.args.get('q')).translate(str.maketrans('', '', "\"@!{}()|-=>"))
    jrs = Document.find((Document.state != "draft") &
                        ((Document.name % query) | (Document.content % query))
                        ).sort_by("creation").all(10)

    jresults = []
    for jdoc in jrs:
        jresults.append({'value': urllib.parse.unquote(jdoc.name),
                         'label': urllib.parse.unquote(jdoc.name),
                         'pretty': pretty_title(urllib.parse.unquote(jdoc.name)),
                         'id': jdoc.pk})

    return jsonify(matching_results=jresults)


@document_bp.route('/browse', methods=['GET'])
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

    try:
        if (request.args.get('q')):
            # Sanitized input for RediSearch
            query = urllib.parse.unquote(request.args.get('q')).translate(str.maketrans('', '', "\"@!{}()|-=>"))
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(
                Query(query + " -@state:{draft}").return_field("name").return_field("creation").sort_by("creation",
                                                                                                        asc=False).paging(
                    offset, per_page))
            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                                    bulma_style='small', prev_label='Previous', next_label='Next page')
        elif (request.args.get('tag')):
            # Sanitized tags for RediSearch: may be empty afterwards, a search like @tags:{""} fails
            tag = request.args.get('tag').translate(str.maketrans('', '', "\"@!{}()|-=>"))
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            if len(tag):
                rs = get_db().ft("document_idx").search(
                    Query("@tags:{" + tag + "} -@state:{draft}").return_field("name").return_field("creation").sort_by(
                        "creation", asc=False).paging(offset, per_page))
                pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                                        bulma_style='small', prev_label='Previous', next_label='Next page')
        else:
            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(
                Query("-@state:{draft}").return_field("name").return_field("creation").sort_by("creation",
                                                                                               asc=False).paging(offset,
                                                                                                                 per_page))
            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                                    bulma_style='small', prev_label='Previous', next_label='Next page')

        # If after sanitizing the input there is nothing to show, redirect to main
        if (rs is not None) and len(rs.docs):
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.name))
                pretty.append(pretty_title(urllib.parse.unquote(key.name)))
                creations.append(datetime.utcfromtimestamp(int(key.creation)).strftime('%Y-%m-%d'))
            keydocument = zip(keys, names, pretty, creations)
        return render_template('browse.html', title=TITLE, desc=DESC, keydocument=keydocument, page=page,
                               per_page=per_page, pagination=pagination)
    except RedisError as err:
        print(err)
        return redirect(url_for("document_bp.browse"))


@document_bp.route('/save', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def save():
    unixtime = int(time.time())
    try:
        doc = Document(
            name=urllib.parse.unquote(request.form['name']),
            content=urllib.parse.unquote(request.form['content']),
            creation=unixtime,
            last=unixtime,
            processable=1,
            state="draft",
            owner=current_user.id,
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

    unixtime = int(time.time())

    # Save the document and change the state TAG to "public"
    document.content = urllib.parse.unquote(request.form['content'])
    document.name = urllib.parse.unquote(request.form['name'])
    document.state = "public"
    document.processable = 1
    document.last = unixtime
    document.save()

    return jsonify(message="Document published")


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
        taglist = document.tags.split(',')

    #  The document hasn't the tag, and it can be added
    if not taglist.count(request.form['tag']) > 0:
        taglist.append(request.form['tag'])
        document.tags = ",".join(taglist)
        document.save()
    else:
        return jsonify(message="Document already tagged", code="warn")

    return jsonify(message="The tag has been added", code="success", tags=taglist)


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
        taglist = document.tags.split(',')
        taglist.remove(request.form['tag'])
        document.tags = ",".join(taglist)
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

    # Create version
    version = Version(
        name=document.name,
        content=document.content,
        creation=document.creation,
        last=document.last,
        owner=document.owner
    )

    document.versions.insert(0, version)

    # Save the document and revert the state TAG to "draft"
    document.content = urllib.parse.unquote(request.form['content'])
    document.name = urllib.parse.unquote(request.form['name'])
    document.state = "draft"
    document.owner = current_user.id
    document.processable = 1
    document.last = unixtime
    document.save()

    return jsonify(message="Document saved as draft")


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

    doc_name = urllib.parse.quote(document.name)
    doc_content = urllib.parse.quote(document.content)
    return render_template('edit.html', title=TITLE, desc=DESC, id=id, name=doc_name,
                           pretty=pretty_title(urllib.parse.unquote(doc_name)), content=doc_content,
                           state=document.state, tags=document.tags, versions=document.versions)


@document_bp.route('/delete/<id>')
@login_required
@requires_access_level(Role.ADMIN)
def delete(id):
    try:
        Document.delete(id)
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

    # If it is a draft, role is editor: make sure the editor owns the draft. Editor can edit the draft
    # If it is a draft, role is admin: can see, edit and publish
    if document.state == 'draft' and document.owner != current_user.id and not current_user.is_admin():
        print("This document is locked for editing, if not an admin, cannot read it")
        return render_template('locked.html', name=document.name), 403
    elif document.state == 'draft' and current_user.is_viewer():
        print("Drafts are locked for viewers")
        return render_template('locked.html', name=document.name), 403

    document.name = urllib.parse.quote(document.name)
    document.content = urllib.parse.quote(document.content)

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

    if get_db().exists("keybase:vss:{}".format(id)):
        keys_and_args = ["keybase:vss:{}".format(id)]
        res = get_db().eval(
            "local vector = redis.call('HMGET',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','vss_idx','*=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres",
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


@document_bp.route('/version/<id>')
@login_required
@requires_access_level(Role.EDITOR)
def version(id):
    return jsonify(message="Version is available")