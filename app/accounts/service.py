import logging
import time
from datetime import datetime, timedelta, timezone

from flask import current_app, has_app_context

from app import db as db_module
from app.config import ConfigError
from app.mail.exceptions import MailError, MailLoginError, MailParseError, MailTimeoutError
from app.mail.imap_client import MailClient
from app.mail.providers import create_mail_provider
from app.matuya.client import MatuyaClient
from app.matuya.exceptions import (
    MatuyaFormParseError,
    MatuyaRequestError,
    MatuyaSubmitError,
)

from .generator import AccountGenerator
from .repository import AccountRepository, DuplicateEmailError
from .tasks import get_task_runner


logger = logging.getLogger(__name__)


class EmailGenerateExhaustedError(RuntimeError):
    pass


class BatchCountError(ValueError):
    pass


ERROR_CONFIG_MISSING = "error.registration.config_missing"
ERROR_MAIL_LOGIN_FAILED = "error.registration.mail_login_failed"
ERROR_MAIL_SERVICE_FAILED = "error.registration.mail_service_failed"
ERROR_MAIL_TIMEOUT = "error.registration.mail_timeout"
ERROR_MAIL_PARSE_FAILED = "error.registration.mail_parse_failed"
ERROR_MATUYA_REQUEST_FAILED = "error.registration.matuya_request_failed"
ERROR_MATUYA_FORM_CHANGED = "error.registration.matuya_form_changed"
ERROR_MATUYA_SUBMIT_FAILED = "error.registration.matuya_submit_failed"
ERROR_EMAIL_CONFLICT_EXHAUSTED = "error.registration.email_conflict_exhausted"
ERROR_INTERRUPTED = "error.registration.interrupted"
ERROR_UNKNOWN = "error.registration.unknown"


class AccountService:
    def __init__(
        self,
        db,
        config=None,
        runner=None,
        mail_client=None,
        mail_provider=None,
        matuya_client=None,
        generator=None,
        app=None,
    ):
        self.db = db
        self.config = config or current_app.config["APP_CONFIG"]
        self.runner = runner
        self.mail_client = mail_client
        self.mail_provider = mail_provider
        self.matuya_client = matuya_client
        self.generator = generator
        self.app = app or (current_app._get_current_object() if has_app_context() else None)

    @classmethod
    def from_current_app(cls):
        app = current_app._get_current_object()
        return cls(
            db_module.get_db(),
            config=app.config["APP_CONFIG"],
            runner=get_task_runner(app),
            app=app,
        )

    def enqueue_single_register(self, created_by):
        account = self._create_unique_account(created_by)
        self._submit_registration(account.id)
        return account

    def enqueue_batch_register(self, count, created_by):
        count = self._validate_batch_count(count)
        accounts = []
        for _ in range(count):
            try:
                accounts.append(self._create_unique_account(created_by))
            except (EmailGenerateExhaustedError, MailError) as exc:
                accounts.append(self._create_failed_account(created_by, exc))
        for account in accounts:
            if account.status == "pending":
                self._submit_registration(account.id)
        return accounts

    def run_registration(self, account_id):
        if self.app is not None and not has_app_context():
            with self.app.app_context():
                task_service = AccountService(
                    db_module.get_db(),
                    config=self.config,
                    runner=self.runner,
                    app=self.app,
                )
                return task_service._run_registration(account_id, task_service.db)
        return self._run_registration(account_id, self.db)

    def list_accounts(self, status=None, bucket=None, page=1, page_size=None):
        page_size = page_size or self.config.page_size_default
        return AccountRepository(self.db).list(
            status=status, bucket=bucket, page=page, page_size=page_size
        )

    def get_account(self, account_id):
        return AccountRepository(self.db).get(account_id)

    def record_copy(self, account_id):
        return AccountRepository(self.db).increment_copy_count(account_id)

    def record_credential_copy(self, account_id, credential):
        account = AccountRepository(self.db).increment_credential_copy_count(
            account_id, credential
        )
        if account.status == "success":
            self.ensure_auto_refill()
        return account

    def mark_interrupted_running_accounts(self):
        AccountRepository(self.db).mark_interrupted_running_accounts()

    def _run_registration(self, account_id, db):
        repo = AccountRepository(db)
        account = repo.mark_running(account_id)
        started = time.monotonic()
        self._log(account, "start", "running", started)
        try:
            self._stage(account, "send_register_mail", self._matuya_client.send_register_mail, account.email)
            register_url = self._stage(
                account, "wait_register_link", self._mail_client.wait_register_link, account.email
            )
            profile = self._stage(account, "generate_profile", self._generator.generate_profile, account.password)
            self._stage(
                account,
                "complete_registration",
                self._matuya_client.complete_registration,
                register_url,
                profile,
            )
            account = repo.mark_success(account_id)
            self._log(account, "complete", "success", started)
            return account
        except Exception as exc:
            error_key = normalize_registration_error(exc)
            account = repo.mark_failed(account_id, error_key)
            self._log(account, "fail", "failed", started, error_key, exc_info=True)
            return account
        finally:
            try:
                self._mail_provider.cleanup_recipient(account.email)
            except MailError:
                logger.info("mail provider cleanup failed after registration", exc_info=True)
            self.ensure_auto_refill(db=db)

    def ensure_auto_refill(self, db=None):
        if not self.config.auto_refill_enabled:
            return []
        target_db = db or self.db
        refill_service = AccountService(
            target_db,
            config=self.config,
            runner=self.runner,
            app=self.app,
        )
        accounts = []
        target_db.execute("begin immediate")
        try:
            repo = AccountRepository(target_db)
            available, in_flight = repo.inventory_counts()
            if available < self.config.auto_refill_threshold:
                cutoff = (
                    datetime.now(timezone.utc)
                    - timedelta(seconds=self.config.auto_refill_failure_cooldown_seconds)
                ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                cooling_down = (
                    self.config.auto_refill_failure_cooldown_seconds > 0
                    and repo.has_recent_failure(cutoff)
                )
                if not cooling_down:
                    count = min(
                        self.config.batch_max_count,
                        max(0, self.config.auto_refill_target - available - in_flight),
                    )
                    for _ in range(count):
                        try:
                            accounts.append(refill_service._create_unique_account(None))
                        except (EmailGenerateExhaustedError, MailError) as exc:
                            accounts.append(refill_service._create_failed_account(None, exc))
            target_db.execute("commit")
        except Exception:
            target_db.execute("rollback")
            raise
        for account in accounts:
            if account.status == "pending":
                refill_service._submit_registration(account.id)
        return accounts

    def _create_unique_account(self, created_by):
        if self.mail_provider is not None:
            return self._create_unique_account_with_provider(created_by)
        if self.mail_client is None:
            self.mail_provider = self._build_mail_provider()
            return self._create_unique_account_with_provider(created_by)
        return self._create_unique_account_with_generator(created_by)

    def _create_unique_account_with_generator(self, created_by):
        repo = AccountRepository(self.db)
        for _ in range(10):
            email = self._generator.generate_email()
            password = self._generator.generate_password()
            try:
                account = repo.create_pending(email, password, created_by)
                self._log(account, "create_account", "pending", time.monotonic())
                return account
            except DuplicateEmailError:
                logger.info("email conflict while creating pending account", extra={"email": email})
        raise EmailGenerateExhaustedError("email generation exhausted")

    def _create_unique_account_with_provider(self, created_by):
        repo = AccountRepository(self.db)
        last_error = None
        for provider in self.mail_provider.providers:
            for _ in range(10):
                email = provider.generate_email()
                password = self._generator.generate_password()
                prepared = False
                try:
                    provider.prepare_recipient(email)
                    prepared = True
                    account = repo.create_pending(email, password, created_by)
                    self._log(account, "create_account", "pending", time.monotonic())
                    return account
                except DuplicateEmailError:
                    logger.info("email conflict while creating pending account", extra={"email": email})
                    if prepared:
                        try:
                            provider.cleanup_recipient(email)
                        except MailError:
                            logger.info("mail provider cleanup failed after email conflict", exc_info=True)
                    continue
                except MailError as exc:
                    last_error = exc
                    logger.info("mail provider failed while preparing recipient", exc_info=True)
                    break
        if last_error is not None:
            raise last_error
        raise EmailGenerateExhaustedError("email generation exhausted")

    def _create_failed_account(self, created_by, exc):
        repo = AccountRepository(self.db)
        generator = AccountGenerator(self._failure_mail_suffix())
        error_key = normalize_registration_error(exc)
        for _ in range(10):
            email = generator.generate_email()
            password = generator.generate_password()
            try:
                account = repo.create_failed(email, password, created_by, error_key)
                self._log(account, "create_account", "failed", time.monotonic(), error_key)
                return account
            except DuplicateEmailError:
                logger.info("email conflict while creating failed account", extra={"email": email})
        raise EmailGenerateExhaustedError("email generation exhausted")

    def _failure_mail_suffix(self):
        if self.config.mail_suffix:
            return self.config.mail_suffix
        if self.config.mail_tm_suffix:
            return self.config.mail_tm_suffix
        return "@failed.local"

    def _submit_registration(self, account_id):
        if self.runner is not None:
            return self.runner.submit(self.run_registration, account_id)
        return None

    def _validate_batch_count(self, count):
        try:
            value = int(count)
        except (TypeError, ValueError) as exc:
            raise BatchCountError("count must be an integer") from exc
        if not 1 <= value <= self.config.batch_max_count:
            raise BatchCountError(
                f"count must be between 1 and {self.config.batch_max_count}"
            )
        return value

    def _stage(self, account, stage, fn, *args):
        started = time.monotonic()
        self._log(account, stage, "running", started)
        result = fn(*args)
        self._log(account, stage, "complete", started)
        return result

    @property
    def _mail_client(self):
        if self.mail_client is None:
            self.mail_client = self._mail_provider
        return self.mail_client

    @property
    def _mail_provider(self):
        if self.mail_provider is None:
            self.mail_provider = self._build_mail_provider()
        return self.mail_provider

    @property
    def _generator(self):
        if self.generator is None:
            self.generator = AccountGenerator(self.config.mail_suffix)
        return self.generator

    def _build_mail_provider(self):
        return create_mail_provider(self.config, generator=self._generator)

    @property
    def _matuya_client(self):
        if self.matuya_client is None:
            self.matuya_client = MatuyaClient(self.config)
        return self.matuya_client

    def _log(self, account, stage, status, started, error=None, exc_info=False):
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "registration account_id=%s email=%s stage=%s status=%s duration_ms=%s error=%s",
            getattr(account, "id", None),
            getattr(account, "email", None),
            stage,
            status,
            duration_ms,
            error or "",
            exc_info=exc_info,
        )


def normalize_registration_error(exc):
    if isinstance(exc, ConfigError):
        return ERROR_CONFIG_MISSING
    if isinstance(exc, MailLoginError):
        return ERROR_MAIL_LOGIN_FAILED
    if isinstance(exc, MailTimeoutError):
        return ERROR_MAIL_TIMEOUT
    if isinstance(exc, MailParseError):
        return ERROR_MAIL_PARSE_FAILED
    if isinstance(exc, MailError):
        return ERROR_MAIL_SERVICE_FAILED
    if isinstance(exc, MatuyaRequestError):
        return ERROR_MATUYA_REQUEST_FAILED
    if isinstance(exc, MatuyaFormParseError):
        return ERROR_MATUYA_FORM_CHANGED
    if isinstance(exc, MatuyaSubmitError):
        return ERROR_MATUYA_SUBMIT_FAILED
    if isinstance(exc, EmailGenerateExhaustedError):
        return ERROR_EMAIL_CONFLICT_EXHAUSTED
    return ERROR_UNKNOWN
