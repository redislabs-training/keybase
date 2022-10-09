import secrets
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__, template_folder="templates")

    app.config["SESSION_TYPE"] = "filesystem"
    app.config.update({'SECRET_KEY': secrets.token_hex(64)})
    CORS(app)

    from app import app as main_blueprint
    app.register_blueprint(main_blueprint)

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

    from .okta.routes import okta_bp
    app.register_blueprint(okta_bp)

    #from .auth.routes import auth_bp
    #app.register_blueprint(auth_bp)

    return app