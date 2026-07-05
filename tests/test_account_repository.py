import pytest

from app.accounts.repository import AccountRepository, DuplicateEmailError


def test_repository_create_pending_and_duplicate(db_conn):
    repo = AccountRepository(db_conn)

    account = repo.create_pending("a@example.invalid", "Secret123", None)

    assert account.id
    assert account.status == "pending"
    with pytest.raises(DuplicateEmailError):
        repo.create_pending("a@example.invalid", "Other123", None)

    failed = repo.create_failed(
        "failed-create@example.invalid",
        "Secret123",
        None,
        "error.registration.mail_service_failed",
    )
    assert failed.status == "failed"
    assert failed.error_message == "error.registration.mail_service_failed"
    assert failed.completed_at


def test_repository_status_updates_and_copy_count(db_conn):
    repo = AccountRepository(db_conn)
    account = repo.create_pending("b@example.invalid", "Secret123", None)

    running = repo.mark_running(account.id)
    assert running.status == "running"
    assert running.started_at

    failed = repo.mark_failed(account.id, "error.registration.mail_timeout")
    assert failed.status == "failed"
    assert failed.error_message == "error.registration.mail_timeout"
    assert failed.completed_at

    running_again = repo.mark_running(account.id)
    assert running_again.status == "running"
    success = repo.mark_success(account.id)
    assert success.status == "success"
    assert success.completed_at
    assert success.error_message is None

    copied = repo.increment_credential_copy_count(account.id, "email")
    copied = repo.increment_credential_copy_count(account.id, "email")
    copied = repo.increment_credential_copy_count(account.id, "password")
    assert copied.copy_count == 3
    assert copied.email_copy_count == 2
    assert copied.password_copy_count == 1
    assert copied.last_email_copied_at
    assert copied.last_password_copied_at


def test_repository_list_filter_pagination_and_interrupted(db_conn):
    repo = AccountRepository(db_conn)
    first = repo.create_pending("first@example.invalid", "Secret123", None)
    second = repo.create_pending("second@example.invalid", "Secret123", None)
    third = repo.create_pending("third@example.invalid", "Secret123", None)
    repo.mark_success(first.id)
    repo.mark_failed(second.id, "error.registration.unknown")
    repo.mark_running(third.id)

    success_page = repo.list(status="success", page=1, page_size=10)
    assert success_page.total == 1
    assert success_page.items[0].email == "first@example.invalid"

    all_page = repo.list(page=2, page_size=2)
    assert all_page.page == 2
    assert all_page.page_size == 2
    assert all_page.total == 3
    assert len(all_page.items) == 1

    repo.mark_interrupted_running_accounts()
    interrupted = repo.get(third.id)
    assert interrupted.status == "failed"
    assert interrupted.error_message == "error.registration.interrupted"


def test_repository_bucket_filters_used_unused_failed(db_conn):
    repo = AccountRepository(db_conn)
    used = repo.create_pending("used@example.invalid", "Secret123", None)
    unused = repo.create_pending("unused@example.invalid", "Secret123", None)
    failed = repo.create_pending("failed@example.invalid", "Secret123", None)
    repo.mark_success(used.id)
    repo.mark_success(unused.id)
    repo.mark_failed(failed.id, "error.registration.unknown")
    repo.increment_credential_copy_count(used.id, "email")
    repo.increment_credential_copy_count(used.id, "password")

    assert repo.list(bucket="used").items[0].email == "used@example.invalid"
    assert repo.list(bucket="failed").items[0].email == "failed@example.invalid"
    assert repo.list(bucket="unused").items[0].email == "unused@example.invalid"
