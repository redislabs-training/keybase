import urllib

from flask import Blueprint, request, jsonify
from flask_login import login_required
from redis_om import NotFoundError

from src.common.config import get_db
from src.document.document import Document
from src.common.utils import requires_access_level, Role

version_bp = Blueprint('version_bp', __name__,
                        template_folder='./templates')

@version_bp.route('/version', methods=['GET'])
@login_required
@requires_access_level(Role.EDITOR)
def version():
    try:
        document = Document.get(request.args.get('pk'))
    except NotFoundError:
        return jsonify(message="The document does not exist"), 404

    for json_doc in document.versions:
        if json_doc.pk == request.args.get('vpk'):
            json_doc.name = urllib.parse.quote(json_doc.name)
            json_doc.content = urllib.parse.quote(json_doc.content)
            # Fetch on-the-fly the username, not persisted in the version
            username = get_db().hmget("keybase:okta:{}".format(json_doc.owner), 'name')
            json_doc.username = username
            return jsonify(json_doc.json())

    return jsonify(message="The version does not exist"), 404