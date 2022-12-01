import urllib.parse
from datetime import datetime

from flask import Blueprint, render_template
from flask_login import (current_user, login_required)

from src.common.config import get_db
from src.common.utils import pretty_title
from src.user import requires_access_level, Role
from src.document.document import Document


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
    docs = None

    # Search for own drafts if not admin
    if not current_user.is_admin():
        jrs = Document.find((Document.state == "draft") &
                            (Document.owner == current_user.id)
                            ).sort_by("-last").all()
    else:
        # And if you are admin, also everybody else's drafts
        jrs = Document.find((Document.state == "draft")).sort_by("-last").all()

    if len(jrs):
        for jdoc in jrs:
            keys.append(jdoc.pk)
            names.append(urllib.parse.unquote(jdoc.name))
            pretty.append(pretty_title(urllib.parse.unquote(jdoc.name)))
            owner.append(get_db().hget("keybase:okta:{}".format(jdoc.owner), "name"))
            updates.append(datetime.utcfromtimestamp(int(jdoc.last)).strftime('%Y-%m-%d %H:%M:%S'))
        docs = zip(keys, names, pretty, owner, updates)

    return render_template("draft.html", drafts=docs)