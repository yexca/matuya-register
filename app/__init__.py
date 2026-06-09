from flask import Flask

from . import db
from .auth.service import AuthService
from .config import load_config
from .logging import init_logging
from .security import init_security


def create_app():
    app = Flask(__name__)
    config = load_config()
    app.config.from_mapping(config.to_flask_config())
    app.config["APP_CONFIG"] = config
    app.secret_key = config.app_secret_key

    init_logging(app)
    db.init_app(app)
    with app.app_context():
        AuthService(db.get_db()).ensure_initial_admin(
            config.admin_username, config.admin_password
        )
    init_security(app)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
