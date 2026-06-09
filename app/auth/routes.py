from flask import Blueprint, redirect, render_template, request, session, url_for

from app import db
from app.i18n import t

from .decorators import login_required
from .service import AuthService


bp = Blueprint("auth", __name__)


@bp.get("/login")
def login():
    return render_template("login.html", error_message=None)


@bp.post("/login")
def login_post():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    user = AuthService(db.get_db()).login(username, password)
    if user is None:
        return (
            render_template("login.html", error_message=t("auth.invalid_credentials")),
            401,
        )
    session["user_id"] = user.id
    session["username"] = user.username
    return redirect(request.args.get("next") or url_for("accounts.index"))


@bp.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
