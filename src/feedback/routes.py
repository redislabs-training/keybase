import time
import urllib
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from redis_om import NotFoundError

from src.common.utils import track_request
from src.document.document import Document
from src.feedback.feedback import Feedback
from src.common.utils import requires_access_level, Role

feedback_bp = Blueprint('feedback_bp', __name__,
                        template_folder='./templates')


@feedback_bp.before_request
def before_request():
    # Track the request in a Redis Stream
    track_request()


@feedback_bp.route('/comment', methods=['POST'])
@login_required
def comment():
    try:
        Document.get(request.form['pk'])
    except NotFoundError:
        return jsonify(message="The document does not exist"), 404

    if not request.form['desc'] or not request.form['msg']:
        return jsonify(message="Missing mandatory data"), 400

    if len(request.form['desc']) < 10:
        return jsonify(message="The description is too short"), 422
    if len(request.form['msg']) < 10:
        return jsonify(message="The message is too short"), 422

    # Create version
    utctime = int(time.time())
    comment = Feedback(
        document=request.form['pk'],
        description=urllib.parse.unquote(request.form['desc']),
        message=urllib.parse.unquote(request.form['msg']),
        creation=utctime,
        reporter=current_user.id
    )

    comment.save()

    return jsonify(message="The feedback has been posted", code="success"), 200


@feedback_bp.route('/feedback', methods=['GET'])
@login_required
@requires_access_level(Role.EDITOR)
def feedback():
    results = []
    state = None

    if request.args.get('state') is not None and \
            request.args.get('state') in ['open', 'implemented', 'rejected']:
        entries = Feedback.find(Feedback.state == request.args.get('state')).sort_by("-creation").all()
        state = request.args.get('state')
    else:
        entries = Feedback.find().sort_by("-creation").all()
        state = None

    for entry in entries:
        results.append({'key': entry.pk,
                        'description': urllib.parse.unquote(entry.description),
                        'state': entry.state.value,
                        'creation': datetime.utcfromtimestamp(int(entry.creation)).strftime('%Y-%m-%d %H:%M:%S'),
                        'docid': entry.document
                        })

    return render_template("feedback/view.html", results=results, state=state)


@feedback_bp.route('/detail', methods=['GET'])
@login_required
@requires_access_level(Role.EDITOR)
def detail():
    try:
        feedback = Feedback.get(request.args.get('pk'))
    except NotFoundError:
        return jsonify(message="The feedback does not exist"), 404

    return jsonify(feedback.dict())


@feedback_bp.route('/response', methods=['POST'])
@login_required
@requires_access_level(Role.EDITOR)
def response():
    try:
        feedback = Feedback.get(request.form['pk'])
    except NotFoundError:
        return jsonify(message="The feedback does not exist"), 404

    if request.form['state'] in ['open', 'implemented', 'rejected']:
        feedback.response = request.form['response']
        feedback.state = request.form['state']
        feedback.save()
    else:
        return jsonify(message="Wrong feedback state", code="error"), 422

    return jsonify(message="The feedback has been responded", code="success"), 200
