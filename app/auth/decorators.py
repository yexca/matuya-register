from functools import wraps

from flask import g, redirect, request, session, url_for

from app.i18n import json_error


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if getattr(g, "current_user", None) is not None:
            return fn(*args, **kwargs)
        if _is_api_request():
            return json_error("error.auth.required", 401)
        return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

    return wrapper


def _is_api_request():
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def current_user_id():
    return session.get("user_id")
