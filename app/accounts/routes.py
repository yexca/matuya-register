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
ALLOWED_BUCKETS = {"unused", "used", "failed"}


@bp.get("/")
@login_required
def index():
    page_args = _pagination_args()
    if page_args[0] is None:
        return page_args[1]
    page, page_size = page_args
    bucket = _bucket_arg()
    if bucket[0] is None and bucket[1] is not None:
        return bucket[1]
    page_obj = AccountService.from_current_app().list_accounts(
        bucket=bucket[0], page=page, page_size=page_size
    )
    return render_template(
        "accounts.html",
        accounts=page_obj,
        bucket_filter=bucket[0],
        serialized_accounts=[serialize_account(item) for item in page_obj.items],
    )


@bp.get("/api/accounts")
@login_required
def list_accounts():
    page_args = _pagination_args()
    if page_args[0] is None:
        return page_args[1]
    page, page_size = page_args
    bucket = _bucket_arg()
    if bucket[0] is None and bucket[1] is not None:
        return bucket[1]
    status = _status_arg()
    if status[0] is None and status[1] is not None:
        return status[1]
    page_obj = AccountService.from_current_app().list_accounts(
        status=status[0], bucket=bucket[0], page=page, page_size=page_size
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
    return _copy_credential(account_id, "email")


@bp.post("/api/accounts/<int:account_id>/copy-email")
@login_required
def copy_email(account_id):
    return _copy_credential(account_id, "email")


@bp.post("/api/accounts/<int:account_id>/copy-password")
@login_required
def copy_password(account_id):
    return _copy_credential(account_id, "password")


def _copy_credential(account_id, credential):
    service = AccountService.from_current_app()
    if service.get_account(account_id) is None:
        return json_error("error.account.not_found", 404)
    account = service.record_credential_copy(account_id, credential)
    return {"account": serialize_account(account)}


def serialize_page(page):
    return {
        "items": [serialize_account(item) for item in page.items],
        "page": page.page,
        "page_size": page.page_size,
        "total": page.total,
    }


def serialize_account(account):
    error_key = account.error_message
    ui_status = display_status(account)
    return {
        "id": account.id,
        "email": account.email,
        "password": account.password,
        "status": ui_status,
        "raw_status": account.status,
        "bucket": account_bucket(account),
        "error_key": error_key,
        "error_message": t(error_key) if error_key else "",
        "copy_count": account.copy_count,
        "last_copied_at": account.last_copied_at,
        "email_copy_count": account.email_copy_count,
        "password_copy_count": account.password_copy_count,
        "last_email_copied_at": account.last_email_copied_at,
        "last_password_copied_at": account.last_password_copied_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
        "started_at": account.started_at,
        "completed_at": account.completed_at,
    }


def account_bucket(account):
    if account.status == AccountStatus.FAILED.value:
        return "failed"
    if (
        account.status == AccountStatus.SUCCESS.value
        and account.email_copy_count >= 1
        and account.password_copy_count >= 1
    ):
        return "used"
    return "unused"


def display_status(account):
    if account.status == AccountStatus.FAILED.value:
        return "failed"
    if account.status in {AccountStatus.PENDING.value, AccountStatus.RUNNING.value}:
        return "pending"
    return account_bucket(account)


def _status_arg():
    status = request.args.get("status", "").strip()
    if not status:
        return "", None
    if status not in ALLOWED_STATUSES:
        return None, json_error("error.validation.status", 400)
    return status, None


def _bucket_arg():
    if "bucket" in request.args:
        bucket = request.args.get("bucket", "").strip()
        if not bucket:
            return "unused", None
        if bucket not in ALLOWED_BUCKETS:
            return None, json_error("error.validation.status", 400)
        return bucket, None

    legacy_status = request.args.get("status", "").strip()
    if not legacy_status:
        return "unused", None
    if legacy_status in ALLOWED_STATUSES:
        # Preserve existing URLs such as ?status=success.
        return "", None
    return None, json_error("error.validation.status", 400)


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
