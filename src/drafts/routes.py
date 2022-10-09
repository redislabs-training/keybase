from redis.commands.search.query import Query
import urllib.parse
from datetime import datetime
from flask import Blueprint, render_template
from flask_login import (current_user, login_required)

from src.user import requires_access_level, Role
from src.common.config import get_db
from src.common.utils import get_analytics, pretty_title

drafts_bp = Blueprint('drafts_bp', __name__,
                     template_folder='./templates')


@drafts_bp.route('/drafts')
@login_required
@requires_access_level(Role.EDITOR)
def drafts():
    keys = []
    names = []
    pretty = []
    owner = []
    updates = []
    drafts = None

    # Search for own drafts if not admin
    if not current_user.is_admin():
        rs = get_db().ft("document_idx").search(
            Query('@state:{draft} @owner:(' + current_user.id + ')').return_field("name").return_field(
                "update").return_field("owner").sort_by("update", asc=False))
    else:
        # And if you are admin, also everybody else's drafts
        rs = get_db().ft("document_idx").search(
            Query('@state:{draft}').return_field("name").return_field("update").return_field("owner").sort_by("update",
                                                                                                              asc=False))

    if len(rs.docs):
        for key in rs.docs:
            keys.append(key.id.split(':')[-1])
            names.append(urllib.parse.unquote(key.name))
            pretty.append(pretty_title(urllib.parse.unquote(key.name)))
            owner.append(get_db().hget("keybase:okta:{}".format(key.owner), "name"))
            updates.append(datetime.utcfromtimestamp(int(key.update)).strftime('%Y-%m-%d %H:%M:%S'))
        drafts = zip(keys, names, pretty, owner, updates)

    return render_template("draft.html", drafts=drafts)