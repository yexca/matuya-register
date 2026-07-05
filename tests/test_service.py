import pytest

from app.accounts.repository import AccountRepository
from app.accounts.service import AccountService, EmailGenerateExhaustedError
from app.accounts.types import RegistrationProfile
from app.mail.exceptions import MailSearchError, MailTimeoutError
from app.matuya.exceptions import MatuyaFormParseError


class FakeMatuyaClient:
    def __init__(self, error=None):
        self.error = error

    def send_register_mail(self, email):
        return True

    def complete_registration(self, register_url, profile):
        if self.error:
            raise self.error
        return True


class FakeMailClient:
    def __init__(self, error=None, fail_recipient=None):
        self.error = error
        self.fail_recipient = fail_recipient

    def wait_register_link(self, recipient):
        if self.error or recipient == self.fail_recipient:
            raise self.error or MailTimeoutError("timeout")
        return "https://example.invalid/complete"


class SequenceGenerator:
    def __init__(self, emails):
        self.emails = list(emails)

    def generate_email(self):
        return self.emails.pop(0)

    def generate_password(self):
        return "Aa123456789012"

    def generate_profile(self, password):
        return RegistrationProfile(
            password=password,
            name_sei="Doe",
            name_mei="Jane",
            kana_sei="Doe",
            kana_mei="Jane",
            phone_a="080",
            phone_e="1234",
            phone_n="5678",
        )


class FakeProvider:
    def __init__(self, name, email, prepare_error=None):
        self.name = name
        self.email = email
        self.prepare_error = prepare_error
        self.prepared = []
        self.cleaned = []

    def generate_email(self):
        return self.email

    def prepare_recipient(self, recipient):
        self.prepared.append(recipient)
        if self.prepare_error:
            raise self.prepare_error

    def wait_register_link(self, recipient):
        return "https://example.invalid/complete"

    def cleanup_recipient(self, recipient):
        self.cleaned.append(recipient)

    def can_handle(self, recipient):
        return recipient == self.email


class FakeFallbackProvider:
    def __init__(self, providers):
        self.providers = providers

    def wait_register_link(self, recipient):
        for provider in self.providers:
            if provider.can_handle(recipient):
                return provider.wait_register_link(recipient)
        raise AssertionError(f"unhandled recipient {recipient}")


def make_service(db_conn, config, **kwargs):
    return AccountService(
        db_conn,
        config=config,
        runner=None,
        mail_client=kwargs.get("mail_client", FakeMailClient()),
        matuya_client=kwargs.get("matuya_client", FakeMatuyaClient()),
        generator=kwargs.get("generator", SequenceGenerator(["a@example.invalid"])),
    )


def test_service_success_path(app, db_conn):
    service = make_service(db_conn, app.config["APP_CONFIG"])
    account = service.enqueue_single_register(created_by=None)

    result = service.run_registration(account.id)

    assert result.status == "success"
    assert result.started_at
    assert result.completed_at


def test_service_matuya_failure_marks_failed(app, db_conn):
    service = make_service(
        db_conn,
        app.config["APP_CONFIG"],
        matuya_client=FakeMatuyaClient(MatuyaFormParseError("changed")),
    )
    account = service.enqueue_single_register(created_by=None)

    result = service.run_registration(account.id)

    assert result.status == "failed"
    assert result.error_message == "error.registration.matuya_form_changed"


def test_service_mail_timeout_marks_failed(app, db_conn):
    service = make_service(
        db_conn,
        app.config["APP_CONFIG"],
        mail_client=FakeMailClient(MailTimeoutError("timeout")),
    )
    account = service.enqueue_single_register(created_by=None)

    result = service.run_registration(account.id)

    assert result.status == "failed"
    assert result.error_message == "error.registration.mail_timeout"


def test_batch_single_failure_does_not_affect_other_accounts(app, db_conn):
    service = AccountService(
        db_conn,
        config=app.config["APP_CONFIG"],
        runner=None,
        mail_client=FakeMailClient(fail_recipient="bad@example.invalid"),
        matuya_client=FakeMatuyaClient(),
        generator=SequenceGenerator(["bad@example.invalid", "good@example.invalid"]),
    )
    bad, good = service.enqueue_batch_register(2, created_by=None)

    bad_result = service.run_registration(bad.id)
    good_result = service.run_registration(good.id)

    assert bad_result.status == "failed"
    assert bad_result.error_message == "error.registration.mail_timeout"
    assert good_result.status == "success"


def test_email_conflict_retries_then_succeeds(app, db_conn):
    AccountRepository(db_conn).create_pending("taken@example.invalid", "Secret123", None)
    service = make_service(
        db_conn,
        app.config["APP_CONFIG"],
        generator=SequenceGenerator(["taken@example.invalid", "fresh@example.invalid"]),
    )

    account = service.enqueue_single_register(created_by=None)

    assert account.email == "fresh@example.invalid"


def test_email_conflict_exhaustion_raises(app, db_conn):
    AccountRepository(db_conn).create_pending("taken@example.invalid", "Secret123", None)
    service = make_service(
        db_conn,
        app.config["APP_CONFIG"],
        generator=SequenceGenerator(["taken@example.invalid"] * 10),
    )

    with pytest.raises(EmailGenerateExhaustedError):
        service.enqueue_single_register(created_by=None)


def test_mail_provider_fallback_creates_account_with_next_provider(app, db_conn):
    bad = FakeProvider(
        "mail_tm",
        "bad@example.invalid",
        prepare_error=MailSearchError("mail service failed"),
    )
    good = FakeProvider("gmail_imap", "good@example.invalid")
    service = AccountService(
        db_conn,
        config=app.config["APP_CONFIG"],
        runner=None,
        mail_provider=FakeFallbackProvider([bad, good]),
        matuya_client=FakeMatuyaClient(),
        generator=SequenceGenerator([]),
    )

    account = service.enqueue_single_register(created_by=None)

    assert account.email == "good@example.invalid"
    assert bad.prepared == ["bad@example.invalid"]
    assert good.prepared == ["good@example.invalid"]
