import secrets
from secrets import compare_digest

from flask import g, request, session

from . import db
from .auth.service import AuthService
from .i18n import json_error


CSRF_SESSION_KEY = "csrf_token"


def init_security(app):
    app.context_processor(lambda: {"csrf_token": csrf_token})

    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        g.current_user = AuthService(db.get_db()).get_current_user(user_id)

    @app.before_request
    def protect_csrf():
        config = app.config["APP_CONFIG"]
        if not config.enable_csrf or request.method != "POST":
            return None
        expected = session.get(CSRF_SESSION_KEY)
        actual = (
            request.headers.get("X-CSRF-Token")
            if request.is_json
            else request.form.get("_csrf_token")
        )
        if not expected or not actual or not compare_digest(expected, actual):
            return json_error("error.csrf.invalid", 400)
        return None

    return app


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token
