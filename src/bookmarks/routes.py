from flask import Blueprint, render_template, request, jsonify
from flask_login import (current_user, login_required)
from datetime import datetime

from src.common.config import get_db
from src.common.utils import pretty_title

bookmarks_bp = Blueprint('bookmarks_bp', __name__,
                        template_folder='./templates')


@bookmarks_bp.route('/bookmark', methods=['POST'])
@login_required
def bookmark():
    # TODO check that the document exists
    bookmarked = get_db().hexists("keybase:bookmark:{}".format(current_user.id), request.form['docid'])
    if (not bookmarked):
        get_db().hmset("keybase:bookmark:{}".format(current_user.id), {request.form['docid']: ""})
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
            hash = get_db().hmget("keybase:kb:{}".format(key), ['name', 'creation'])
            docs.append(key)
            names.append(hash[0])
            pretty.append(pretty_title(hash[0]))
            creations.append(datetime.utcfromtimestamp(int(hash[1])).strftime('%Y-%m-%d %H:%M:%S'))
        if (cursor == 0):
            break

    if len(docs):
        bookmarks = zip(docs, names, pretty, creations)
    return render_template("bookmark.html", bookmarks=bookmarks)