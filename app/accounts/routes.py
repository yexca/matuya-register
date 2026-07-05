from flask import Blueprint, current_app, render_template, request, session

from app.i18n import json_error, t
from app.mail.exceptions import MailError

from app.auth.decorators import login_required
from .service import (
    AccountService,
    BatchCountError,
    EmailGenerateExhaustedError,
    normalize_registration_error,
)
from .types import AccountStatus


bp = Blueprint("accounts", __name__)
ALLOWED_STATUSES = {status.value for status in AccountStatus}


@bp.get("/")
@login_required
def index():
    page_args = _pagination_args()
    if page_args[0] is None:
        return page_args[1]
    page, page_size = page_args
    status = _status_arg()
    if status[0] is None and status[1] is not None:
        return status[1]
    page_obj = AccountService.from_current_app().list_accounts(
        status=status[0], page=page, page_size=page_size
    )
    return render_template(
        "accounts.html",
        accounts=page_obj,
        status_filter=status[0] or "",
        serialized_accounts=[serialize_account(item) for item in page_obj.items],
    )


@bp.get("/api/accounts")
@login_required
def list_accounts():
    page_args = _pagination_args()
    if page_args[0] is None:
        return page_args[1]
    page, page_size = page_args
    status = _status_arg()
    if status[0] is None and status[1] is not None:
        return status[1]
    page_obj = AccountService.from_current_app().list_accounts(
        status=status[0], page=page, page_size=page_size
    )
    return serialize_page(page_obj)


@bp.post("/api/register")
@login_required
def register_single():
    try:
        account = AccountService.from_current_app().enqueue_single_register(
            session.get("user_id")
        )
    except (EmailGenerateExhaustedError, MailError) as exc:
        error = normalize_registration_error(exc)
        return json_error(error, 409 if isinstance(exc, EmailGenerateExhaustedError) else 502)
    return {"account": serialize_account(account)}, 202


@bp.post("/api/register-batch")
@login_required
def register_batch():
    payload = request.get_json(silent=True) or request.form
    try:
        accounts = AccountService.from_current_app().enqueue_batch_register(
            payload.get("count"), session.get("user_id")
        )
    except BatchCountError:
        return json_error(
            "error.validation.count",
            400,
            max=current_app.config["APP_CONFIG"].batch_max_count,
        )
    except (EmailGenerateExhaustedError, MailError) as exc:
        error = normalize_registration_error(exc)
        return json_error(error, 409 if isinstance(exc, EmailGenerateExhaustedError) else 502)
    return {"accounts": [serialize_account(account) for account in accounts]}, 202


@bp.get("/api/accounts/<int:account_id>")
@login_required
def get_account(account_id):
    account = AccountService.from_current_app().get_account(account_id)
    if account is None:
        return json_error("error.account.not_found", 404)
    return {"account": serialize_account(account)}


@bp.post("/api/accounts/<int:account_id>/copy-account")
@login_required
def copy_account(account_id):
    service = AccountService.from_current_app()
    if service.get_account(account_id) is None:
        return json_error("error.account.not_found", 404)
    return {"account": serialize_account(service.record_copy(account_id))}


def serialize_page(page):
    return {
        "items": [serialize_account(item) for item in page.items],
        "page": page.page,
        "page_size": page.page_size,
        "total": page.total,
    }


def serialize_account(account):
    error_key = account.error_message
    return {
        "id": account.id,
        "email": account.email,
        "password": account.password,
        "status": account.status,
        "error_key": error_key,
        "error_message": t(error_key) if error_key else "",
        "copy_count": account.copy_count,
        "last_copied_at": account.last_copied_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
        "started_at": account.started_at,
        "completed_at": account.completed_at,
    }


def _status_arg():
    status = request.args.get("status", "").strip()
    if not status:
        return "", None
    if status not in ALLOWED_STATUSES:
        return None, json_error("error.validation.status", 400)
    return status, None


def _pagination_args():
    config = current_app.config["APP_CONFIG"]
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", str(config.page_size_default)))
    except ValueError:
        return None, json_error("error.validation.pagination", 400)
    if page < 1 or page_size < 1 or page_size > config.page_size_max:
        return None, json_error("error.validation.pagination", 400)
    return page, page_size
