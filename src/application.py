import secrets

from flask import Flask, render_template
from flask_cors import CORS
from datetime import datetime
from flask_breadcrumbs import Breadcrumbs
from werkzeug.exceptions import HTTPException
import logging
import redis

from src.common.config import CFG_AUTHENTICATOR
from src.common.utils import track_errors, get_db

from redis_om import (Migrator)
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition

# These 2 imports are needed for OM; if removed, OM won't create indexes
from src.document.document import Document, Version, CurrentVersion
from src.feedback.feedback import Feedback


def create_app():
    app = Flask(__name__, template_folder="templates")
    Breadcrumbs(app=app)
    app.config["SESSION_TYPE"] = "filesystem"
    app.config.update({'SECRET_KEY': secrets.token_hex(64)})
    app.url_map.strict_slashes = False
    CORS(app)

    from .main import main_bp
    app.register_blueprint(main_bp)

    from .api.routes import api_bp
    app.register_blueprint(api_bp)

    from .bookmarks.routes import bookmarks_bp
    app.register_blueprint(bookmarks_bp)

    from .drafts.routes import drafts_bp
    app.register_blueprint(drafts_bp)

    from .analytics.routes import analytics_bp
    app.register_blueprint(analytics_bp)

    from .admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    from .document.routes import document_bp
    app.register_blueprint(document_bp)

    from .version.routes import version_bp
    app.register_blueprint(version_bp)

    from .feedback.routes import feedback_bp
    app.register_blueprint(feedback_bp)

    from .public.routes import public_bp
    app.register_blueprint(public_bp)

    if CFG_AUTHENTICATOR == 'auth':
        from .auth.routes import auth_bp
        app.register_blueprint(auth_bp)
    else:
        from .okta.routes import auth_bp
        app.register_blueprint(auth_bp)

    # Setup gunicorn logging
    gunicorn_error_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_error_logger.handlers)
    app.logger.setLevel(logging.INFO)

    # Reading the list of indexes for eventual creation
    indexes = get_db().execute_command("FT._LIST")

    if "document_idx" not in indexes:
        app.logger.info("The index document_idx does not exist, creating it")
        Migrator().run()

    if "feedback_idx" not in indexes:
        app.logger.info("The index feedback_idx does not exist, creating it")
        Migrator().run()

    if "user_idx" not in indexes:
        app.logger.info("The index user_idx does not exist, creating it")
        index_def = IndexDefinition(prefix=["keybase:okta"])
        schema = (TextField("name"), TagField("group"))
        get_db().ft('user_idx').create_index(schema, definition=index_def)

    if "vss_idx" not in indexes:
        app.logger.info("The index vss_idx does not exist, creating it")
        index_def = IndexDefinition(prefix=["keybase:vss"])
        schema = (TagField("state"),
                  TagField("privacy"),
                  VectorField("content_embedding", "HNSW", {"TYPE": "FLOAT32", "DIM": 768, "DISTANCE_METRIC": "L2"}))
        get_db().ft('vss_idx').create_index(schema, definition=index_def)

    @app.template_filter('ctime')
    def timectime(s):
        date_time = datetime.fromtimestamp(s)
        return date_time.strftime("%B %d %Y, %H:%M")

    @app.errorhandler(Exception)
    def handle_exception(e):
        # database error
        if isinstance(e, redis.exceptions.ConnectionError):
            return render_template('61.html'), 500

        # pass through HTTP errors
        if isinstance(e, HTTPException):
            return render_template('404.html'), e.code

        # now you're handling non-HTTP exceptions only
        track_errors(e)
        return render_template('500.html'), 500

    app.logger.info('Redis Knowledge Base started!')

    return app
