from flask import Blueprint, render_template, request, jsonify
from flask_login import (current_user, login_required)
from datetime import datetime
from redis_om import NotFoundError

from src.common.config import get_db
from src.common.utils import pretty_title, track_request
from src.document.document import Document

bookmarks_bp = Blueprint('bookmarks_bp', __name__,
                         template_folder='./templates')


@bookmarks_bp.before_request
def before_request():
    # Track the request in a Redis Stream
    track_request()


@bookmarks_bp.route('/bookmark', methods=['POST'])
@login_required
def bookmark():
    try:
        Document.get(request.form['docid'])
    except NotFoundError:
        return jsonify(message="Document does not exist", hasbookmark=0), 404

    bookmarked = get_db().hexists("keybase:bookmark:{}".format(current_user.id), request.form['docid'])
    if (not bookmarked):
        get_db().hset("keybase:bookmark:{}".format(current_user.id), mapping={request.form['docid']: ""})
        return jsonify(message="Bookmark created", hasbookmark=1)
    else:
        get_db().hdel("keybase:bookmark:{}".format(current_user.id), request.form['docid'])
        return jsonify(message="Bookmark removed", hasbookmark=0)


@bookmarks_bp.route('/bookmarks')
@login_required
def bookmarks():
    docs = []
    names = []
    creations = []
    pretty = []
    bookmarks = None
    cursor = 0

    while True:
        cursor, keys = get_db().hscan("keybase:bookmark:{}".format(current_user.id), cursor, count=20)
        for key in keys:
            doc = Document.get(key)
            docs.append(key)
            names.append(doc.editorversion.name)
            pretty.append(pretty_title(doc.editorversion.name))
            creations.append(datetime.utcfromtimestamp(int(doc.creation)).strftime('%Y-%m-%d %H:%M:%S'))
        if cursor == 0:
            break

    if len(docs):
        bookmarks = zip(docs, names, pretty, creations)
    return render_template("bookmark.html", bookmarks=bookmarks)
