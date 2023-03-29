from flask import Blueprint, Response, request, jsonify
from functools import wraps

from src.common.utils import get_db

api_bp = Blueprint('api_bp', __name__)


def token_required(req):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print(req.headers)
            if not "X-Api-Key" in req.headers or not "X-Api-Secret-Key" in req.headers:
                return Response(response="Missing tokens", status=401)
            secret_token = get_db().hget("keybase:api:token", str(req.headers.get("X-Api-Key")))
            if req.headers.get("X-Api-Secret-Key") != secret_token:
                return Response(response="Unauthorized", status=403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@api_bp.route('/api/events/', methods=['GET'])
@token_required(request)
def api_events():
    if not request.args.get("min") or not request.args.get("max"):
        return jsonify(response="Incomplete request"), 422
    if request.args.get("min") and request.args.get("max"):
        events = get_db().xrange("keybase:requests", request.args.get("min"), request.args.get("max"))
        return jsonify(response="Range request completed", events=events), 200

