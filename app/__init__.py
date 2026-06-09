from flask import Flask

from . import db
from . import i18n
from .accounts.routes import bp as accounts_bp
from .auth.routes import bp as auth_bp
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
    i18n.init_i18n(app)
    init_security(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(accounts_bp)

    return app
