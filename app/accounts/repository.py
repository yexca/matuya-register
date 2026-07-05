import sqlite3

from app import db as db_module

from .types import Account, AccountStatus, Page


class DuplicateEmailError(ValueError):
    pass


class AccountRepository:
    def __init__(self, db):
        self.db = db

    def create_pending(self, email, password, created_by):
        now = db_module.utc_now_iso()
        try:
            cursor = self.db.execute(
                """
                insert into matuya_accounts (
                  email, password, status, created_by, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?)
                """,
                (email, password, AccountStatus.PENDING.value, created_by, now, now),
            )
        except sqlite3.IntegrityError as exc:
            if "matuya_accounts.email" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise DuplicateEmailError(email) from exc
            raise
        return self.get(cursor.lastrowid)

    def create_failed(self, email, password, created_by, error_message):
        now = db_module.utc_now_iso()
        try:
            cursor = self.db.execute(
                """
                insert into matuya_accounts (
                  email, password, status, error_message, created_by,
                  completed_at, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    password,
                    AccountStatus.FAILED.value,
                    (error_message or "")[:500],
                    created_by,
                    now,
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            if "matuya_accounts.email" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise DuplicateEmailError(email) from exc
            raise
        return self.get(cursor.lastrowid)

    def get(self, account_id):
        row = self.db.execute(
            "select * from matuya_accounts where id = ?", (account_id,)
        ).fetchone()
        return _to_account(row)

    def list(self, status=None, bucket=None, page=1, page_size=20):
        page = max(1, int(page))
        page_size = max(1, int(page_size))
        offset = (page - 1) * page_size
        params = []
        where_parts = []
        if status:
            where_parts.append("status = ?")
            params.append(_status_value(status))
        if bucket:
            where_parts.append(_bucket_where(bucket))
        where = "where " + " and ".join(where_parts) if where_parts else ""
        total = self.db.execute(
            f"select count(*) from matuya_accounts {where}", params
        ).fetchone()[0]
        rows = self.db.execute(
            f"""
            select * from matuya_accounts
            {where}
            order by created_at desc, id desc
            limit ? offset ?
            """,
            (*params, page_size, offset),
        ).fetchall()
        return Page([_to_account(row) for row in rows], page, page_size, total)

    def mark_running(self, account_id):
        now = db_module.utc_now_iso()
        self.db.execute(
            """
            update matuya_accounts
            set status = ?, started_at = coalesce(started_at, ?), updated_at = ?
            where id = ? and status in (?, ?)
            """,
            (
                AccountStatus.RUNNING.value,
                now,
                now,
                account_id,
                AccountStatus.PENDING.value,
                AccountStatus.FAILED.value,
            ),
        )
        return self.get(account_id)

    def mark_success(self, account_id):
        now = db_module.utc_now_iso()
        self.db.execute(
            """
            update matuya_accounts
            set status = ?, error_message = null, completed_at = ?, updated_at = ?
            where id = ?
            """,
            (AccountStatus.SUCCESS.value, now, now, account_id),
        )
        return self.get(account_id)

    def mark_failed(self, account_id, error_message):
        now = db_module.utc_now_iso()
        self.db.execute(
            """
            update matuya_accounts
            set status = ?, error_message = ?, completed_at = ?, updated_at = ?
            where id = ?
            """,
            (AccountStatus.FAILED.value, (error_message or "")[:500], now, now, account_id),
        )
        return self.get(account_id)

    def increment_copy_count(self, account_id):
        return self.increment_credential_copy_count(account_id, "email")

    def increment_credential_copy_count(self, account_id, credential):
        now = db_module.utc_now_iso()
        if credential == "email":
            count_column = "email_copy_count"
            time_column = "last_email_copied_at"
        elif credential == "password":
            count_column = "password_copy_count"
            time_column = "last_password_copied_at"
        else:
            raise ValueError("credential must be email or password")
        self.db.execute(
            f"""
            update matuya_accounts
            set {count_column} = {count_column} + 1,
                {time_column} = ?,
                copy_count = email_copy_count + password_copy_count + 1,
                last_copied_at = ?,
                updated_at = ?
            where id = ?
            """,
            (now, now, now, account_id),
        )
        return self.get(account_id)

    def mark_interrupted_running_accounts(self):
        now = db_module.utc_now_iso()
        self.db.execute(
            """
            update matuya_accounts
            set status = ?, error_message = ?, completed_at = ?, updated_at = ?
            where status in (?, ?)
            """,
            (
                AccountStatus.FAILED.value,
                "error.registration.interrupted",
                now,
                now,
                AccountStatus.PENDING.value,
                AccountStatus.RUNNING.value,
            ),
        )


def _status_value(status):
    if isinstance(status, AccountStatus):
        return status.value
    return str(status)


def _bucket_where(bucket):
    if bucket == "failed":
        return "status = 'failed'"
    if bucket == "used":
        return (
            "status = 'success' "
            "and email_copy_count >= 1 "
            "and password_copy_count >= 1"
        )
    if bucket == "unused":
        return (
            "status in ('pending', 'running', 'success') "
            "and not (status = 'success' "
            "and email_copy_count >= 1 "
            "and password_copy_count >= 1)"
        )
    raise ValueError("bucket must be unused, used, or failed")


def _to_account(row):
    if row is None:
        return None
    columns = row.keys()
    email_copy_count = (
        row["email_copy_count"] if "email_copy_count" in columns else row["copy_count"]
    )
    password_copy_count = (
        row["password_copy_count"] if "password_copy_count" in columns else 0
    )
    last_email_copied_at = (
        row["last_email_copied_at"]
        if "last_email_copied_at" in columns
        else row["last_copied_at"]
    )
    last_password_copied_at = (
        row["last_password_copied_at"]
        if "last_password_copied_at" in columns
        else None
    )
    return Account(
        id=row["id"],
        email=row["email"],
        password=row["password"],
        status=row["status"],
        error_message=row["error_message"],
        copy_count=max(row["copy_count"], email_copy_count + password_copy_count),
        last_copied_at=row["last_copied_at"],
        email_copy_count=email_copy_count,
        password_copy_count=password_copy_count,
        last_email_copied_at=last_email_copied_at,
        last_password_copied_at=last_password_copied_at,
        created_by=row["created_by"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
