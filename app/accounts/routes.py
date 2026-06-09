from flask import Blueprint, render_template

from app.auth.decorators import login_required


bp = Blueprint("accounts", __name__)


@bp.get("/")
@login_required
def index():
    return render_template("base.html")


@bp.get("/api/accounts")
@login_required
def list_accounts():
    return {"items": [], "page": 1, "page_size": 0, "total": 0}
