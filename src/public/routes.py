import json

import flask
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_paginate import Pagination, get_page_args
from redis import RedisError
from datetime import datetime
import urllib.parse
from redis.commands.search.query import Query
from redis_om import NotFoundError

from src.common.config import get_db
from src.common.utils import pretty_title
from src.document.document import Document

public_bp = Blueprint('public_bp', __name__,
                        template_folder='./themes/redis/templates',
                        static_folder='./themes/redis/static',
                        static_url_path='/theme')


@public_bp.route('/search', methods=['GET'])
def search():
    # Sanitize input for RediSearch
    query = urllib.parse.unquote(request.args.get('q')).translate(str.maketrans('', '', "\"@!{}()|-=>"))

    rs = get_db().ft("document_idx")\
            .search(Query(query + " @privacy:{public} -@state:{draft}")
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


@public_bp.route('/public', methods=['GET'])
def public():
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
            catfilter, tagfilter, queryfilter, sortbyfilter = "", "", "", False

            # Check the ordering
            if flask.request.args.get('asc') == "true":
                sortbyfilter = True
                asc = 1

            # Sanitized input for RediSearch
            if flask.request.args.get('q'):
                queryfilter = urllib.parse.unquote(flask.request.args.get('q')).translate(str.maketrans('', '', "\"@!{}()|-=>"))

            # If the category is good, can be processed and set in the UI
            if flask.request.args.get('cat'):
                if get_db().hexists("keybase:categories", flask.request.args.get('cat')):
                    catfilter = " @category:{"+flask.request.args.get('cat')+"} "
                    category = flask.request.args.get('cat')

            # Sanitized tags for RediSearch: may be empty afterwards, a search like @tags:{""} fails
            if flask.request.args.get('tag'):
                tag = flask.request.args.get('tag').translate(str.maketrans('', '', "\"@!{}()|-=>"))
                tagfilter = " @tags:{" + tag + "} "

            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(
                Query(queryfilter + catfilter + tagfilter + " @privacy:{public} -@state:{draft}")
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
        return render_template('public.html', title=TITLE, desc=DESC, categories=categories, keydocument=keydocument, page=page,
                               per_page=per_page, pagination=pagination, category=category, asc=asc)
    except RedisError as err:
        print(err)
        return redirect(url_for("public_bp.public"))


@public_bp.route('/kb/<id>', defaults={'prettyurl': None})
@public_bp.route('/kb/<id>/<prettyurl>')
def kb(id, prettyurl):
    keys = []
    names = []
    pretty = []
    suggestlist = None

    try:
        documents = get_db().json().get('keybase:json:{}'.format(id), '$.currentversion', '$.keyword', '$.description', '$.privacy', '$.state')

        # Check the document is public and review or published
        if ((documents['$.state'][0] == 'published' or documents['$.state'][0] == 'review') and documents['$.privacy'][0] == 'public'):
            document=documents['$.currentversion'][0]
        else:
            return redirect(url_for('public_bp.public')), 403
    except NotFoundError:
        return redirect(url_for('public_bp.public')), 404

    TITLE = document['name']
    document['name'] = urllib.parse.quote(document['name'])
    document['content'] = urllib.parse.quote(document['content'])
    document['keyword'] = documents['$.keyword'][0]
    document['description'] = documents['$.description'][0]

    # The document can be rendered, count the visit
    get_db().ts().add("keybase:docview:{}".format(id), "*", 1, duplicate_policy='first')

    if get_db().hexists("keybase:vss:{}".format(id), "content_embedding"):
        keys_and_args = ["keybase:vss:{}".format(id)]
        res = get_db().eval(
            "local vector = redis.call('HMGET',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','vss_idx','@privacy:{public}=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres",
            1, *keys_and_args)
        it = iter(res[1:])
        for x in it:
            keys.append(str(x.split(':')[-1]))
            docName = str(next(it)[3])
            names.append(docName)
            pretty.append(pretty_title(docName))
        suggestlist = zip(keys, names, pretty)

    return render_template('kb.html', title=TITLE, docid=id, document=document,
                           suggestlist=suggestlist)