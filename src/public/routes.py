import flask
from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_paginate import Pagination, get_page_args
from redis import RedisError
from datetime import datetime
import urllib.parse
from redis.commands.search.query import Query
from flask_login import (current_user, login_required)

from src.common.config import THEME
from src.common.utils import get_db, pretty_title, parse_query_string
from flask_breadcrumbs import register_breadcrumb, default_breadcrumb_root

public_bp = Blueprint('public_bp', __name__,
                      template_folder='./themes/'+THEME+'/templates',
                      static_folder='./themes/'+THEME+'/static',
                      static_url_path='/theme')

default_breadcrumb_root(public_bp, '.')


def get_bread_path(*args, **kwargs):
    pathlist = list(filter(None, flask.request.path.split('/')))
    if pathlist[0] == 'kb':
        cat = get_db().json().get('keybase:json:{}'.format(pathlist[1]), '$.category')
        # make sure the document has a category
        if cat[0] is not None:
            catname = get_db().hget('keybase:categories', cat[0])
            return [{'text': 'home', 'url': url_for("public_bp.landing")},
                    {'text': catname, 'url': url_for("public_bp.public", cat=cat[0])}]

    # Search can come with a category, but let's consider a pure search to define the breadcrumb
    if flask.request.args.get('q'):
        return [{'text': 'home', 'url': url_for("public_bp.landing")},
                {'text': 'search: "' + urllib.parse.unquote(flask.request.args.get('q')) + '"', 'url': ''}]

    if flask.request.args.get('cat'):
        catname = get_db().hget("keybase:categories", flask.request.args.get('cat'))
        catnamelabel = catname if catname is not None else 'all categories'
        return [{'text': 'home', 'url': url_for("public_bp.landing")},
                {'text': catnamelabel}]

    if flask.request.args.get('tag'):
        return [{'text': 'home', 'url': url_for("public_bp.landing")},
                {'text': flask.request.args.get('tag')}]

    return [{'text': 'home', 'url': url_for("public_bp.landing")}]


@public_bp.route('/', methods=['GET'])
def landing():
    if not current_user.is_authenticated:
        return render_template('index.html')

    categories = get_db().hgetall("keybase:categories")
    return render_template('landing.html', categories=categories)


@public_bp.route('/search', methods=['GET'])
@login_required
def search():
    # Sanitize input for RediSearch
    queryfilter = parse_query_string(flask.request.args.get('q'))
    query = "@currentversion_name_fts|currentversion_content_fts:'" + queryfilter + "'"
    rs = get_db().ft("document_idx") \
        .search(Query(query + " @privacy:{public} -@state:{draft}")
                .return_field("currentversion_name")
                .sort_by("updated", asc=False)
                .paging(0, 10))

    results = []

    for doc in rs.docs:
        results.append({'value': urllib.parse.unquote(doc.currentversion_name),
                        'label': urllib.parse.unquote(doc.currentversion_name),
                        'pretty': pretty_title(urllib.parse.unquote(doc.currentversion_name)),
                        'id': doc.id.split(':')[-1]})

    return jsonify(matching_results=results)


@public_bp.route('/public', methods=['GET'])
@register_breadcrumb(public_bp, '.', '', dynamic_list_constructor=get_bread_path)
@login_required
def public():
    title = "List documents"
    desc = "Listing documents"
    keys = []
    names = []
    pretty = []
    updated = []
    keydocument = None
    pagination = None
    noresultmsg = None
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
                noresultmsg = urllib.parse.unquote(flask.request.args.get('q'))
                queryfilter = parse_query_string(flask.request.args.get('q'))
                queryfilter = "@currentversion_name_fts|currentversion_content_fts:'" + queryfilter + "'"
            # If the category is good, can be processed and set in the UI
            if flask.request.args.get('cat'):
                if get_db().hexists("keybase:categories", flask.request.args.get('cat')):
                    catfilter = " @category:{" + flask.request.args.get('cat') + "} "
                    category = flask.request.args.get('cat')

            # Sanitized tags for RediSearch: may be empty afterwards, a search like @tags:{""} fails
            if flask.request.args.get('tag'):
                tag = flask.request.args.get('tag').translate(str.maketrans('', '', "\"@!{}()|-=>"))
                tagfilter = " @tags:{" + tag + "} "

            page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
            rs = get_db().ft("document_idx").search(
                Query(queryfilter + catfilter + tagfilter + " @privacy:{public} -@state:{draft}")
                .return_field("currentversion_name")
                .return_field("updated")
                .sort_by("updated", asc=sortbyfilter)
                .paging(offset, per_page))

            pagination = Pagination(page=page, per_page=per_page, total=rs.total, css_framework='bulma',
                                    bulma_style='small', prev_label='Previous', next_label='Next page')

        # If after sanitizing the input there is nothing to show, redirect to no results page
        if (rs is not None) and len(rs.docs):
            for key in rs.docs:
                keys.append(key.id.split(':')[-1])
                names.append(urllib.parse.unquote(key.currentversion_name))
                pretty.append(pretty_title(urllib.parse.unquote(key.currentversion_name)))
                updated.append(datetime.utcfromtimestamp(int(key.updated)).strftime('%Y-%m-%d'))
            keydocument = zip(keys, names, pretty, updated)

            # Get the categories
            categories = get_db().hgetall("keybase:categories")
            return render_template('public.html',
                                   title=title,
                                   desc=desc,
                                   categories=categories,
                                   keydocument=keydocument,
                                   page=page,
                                   per_page=per_page,
                                   pagination=pagination,
                                   category=category,
                                   asc=asc)
        else:
            # Get the categories
            categories = get_db().hgetall("keybase:categories")
            return render_template('noresults.html', title="No result found", desc="No result found",
                                   categories=categories, noresultmsg=noresultmsg)

    except RedisError as err:
        print(err)
        return redirect(url_for("public_bp.public"))


@public_bp.route('/kb/<pk>', defaults={'prettyurl': None})
@public_bp.route('/kb/<pk>/<prettyurl>')
@register_breadcrumb(public_bp, '.', '', dynamic_list_constructor=get_bread_path)
@login_required
def kb(pk, prettyurl):
    keys = []
    names = []
    pretty = []
    suggestlist = None

    documents = get_db().json().get('keybase:json:{}'.format(pk), '$.currentversion', '$.keyword', '$.description',
                                    '$.privacy', '$.state', '$.tags', '$.updated', '$.category')
    if documents is None:
        return render_template('404.html'), 404

    # Check the document is public and review or published
    if not ((documents['$.state'][0] == 'published' or documents['$.state'][0] == 'review') and documents['$.privacy'][0] == 'public'):
        return redirect(url_for('public_bp.landing')), 403

    # All fine, read categories
    categories = get_db().hgetall("keybase:categories")

    document = documents['$.currentversion'][0]
    title = document['name']
    document['name'] = urllib.parse.quote(document['name'])
    document['content'] = urllib.parse.quote(document['content'])
    document['keyword'] = documents['$.keyword'][0]
    document['tags'] = documents['$.tags'][0]
    document['description'] = documents['$.description'][0]
    if documents['$.category'][0] is not None:
        document['catid'] = documents['$.category'][0]
        document['catname'] = categories[documents['$.category'][0]]
    document['updated'] = datetime.utcfromtimestamp(int(documents['$.updated'][0])).strftime('%d, %b %Y')

    # The document can be rendered, count the visit
    get_db().ts().add("keybase:docview:{}".format(pk), "*", 1, duplicate_policy='first')

    if get_db().hexists("keybase:vss:{}".format(pk), "content_embedding"):
        keys_and_args = ["keybase:vss:{}".format(pk)]
        res = get_db().eval(
            "local vector = redis.call('HMGET',KEYS[1], 'content_embedding') local searchres = redis.call('FT.SEARCH','vss_idx','(@state:{published|review} @privacy:{public})=>[KNN 6 @content_embedding $B AS score]','PARAMS','2','B',vector[1], 'SORTBY', 'score', 'ASC', 'LIMIT', 1, 6,'RETURN',2,'score','name','DIALECT',2) return searchres",
            1, *keys_and_args)
        it = iter(res[1:])
        for x in it:
            keys.append(str(x.split(':')[-1]))
            docname = str(next(it)[3])
            names.append(docname)
            pretty.append(pretty_title(docname))
        suggestlist = zip(keys, names, pretty)

    return render_template('kb.html',
                           title=title,
                           categories=categories,
                           docid=pk,
                           document=document,
                           suggestlist=suggestlist)
