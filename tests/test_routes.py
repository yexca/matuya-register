from conftest import csrf_token

from app.accounts.repository import AccountRepository
from app.accounts.types import Account
import app.accounts.routes as account_routes


def test_register_api_returns_202(client, login, monkeypatch):
    login()
    token = csrf_token(client)
    account = Account(
        id=99,
        email="new@example.invalid",
        password="Aa123456789012",
        status="pending",
        error_message=None,
        copy_count=0,
        last_copied_at=None,
        email_copy_count=0,
        password_copy_count=0,
        last_email_copied_at=None,
        last_password_copied_at=None,
        created_by=1,
        started_at=None,
        completed_at=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    class FakeService:
        def enqueue_single_register(self, created_by):
            return account

    monkeypatch.setattr(
        account_routes.AccountService,
        "from_current_app",
        classmethod(lambda cls: FakeService()),
    )

    response = client.post("/api/register", json={}, headers={"X-CSRF-Token": token})

    assert response.status_code == 202
    assert response.json["account"]["email"] == "new@example.invalid"
    assert response.json["account"]["status"] == "pending"


def test_register_batch_count_validation(client, login):
    login()
    response = client.post(
        "/api/register-batch",
        json={"count": 0},
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert response.status_code == 400
    assert response.json["error"] == "error.validation.count"


def test_register_batch_returns_requested_count(client, login, monkeypatch):
    login()
    token = csrf_token(client)
    accounts = [
        Account(
            id=index,
            email=f"new-{index}@example.invalid",
            password="Aa123456789012",
            status="pending",
            error_message=None,
            copy_count=0,
            last_copied_at=None,
            email_copy_count=0,
            password_copy_count=0,
            last_email_copied_at=None,
            last_password_copied_at=None,
            created_by=1,
            started_at=None,
            completed_at=None,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        for index in range(1, 4)
    ]

    class FakeService:
        def enqueue_batch_register(self, count, created_by):
            assert int(count) == 3
            return accounts

    monkeypatch.setattr(
        account_routes.AccountService,
        "from_current_app",
        classmethod(lambda cls: FakeService()),
    )

    response = client.post(
        "/api/register-batch",
        json={"count": 3},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 202
    assert len(response.json["accounts"]) == 3


def test_get_accounts_returns_pagination(client, login, db_conn):
    AccountRepository(db_conn).create_pending("page@example.invalid", "Secret123", None)
    login()

    response = client.get("/api/accounts?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["email"] == "page@example.invalid"


def test_accounts_page_uses_compact_rows(client, login, db_conn):
    AccountRepository(db_conn).create_pending("compact@example.invalid", "Secret123", None)
    login()

    response = client.get("/")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert 'class="account-row"' in html
    assert 'data-detail-copy="email"' in html
    assert 'data-detail-copy="password"' in html
    assert 'class="detail-advanced"' in html
    assert html.count('data-detail-copy=') == 2
    assert "data-details" in html


def test_get_account_not_found_returns_404(client, login):
    login()

    response = client.get("/api/accounts/999")

    assert response.status_code == 404
    assert response.json["error"] == "error.account.not_found"


def test_copy_account_increments_copy_count(client, login, db_conn):
    account = AccountRepository(db_conn).create_pending(
        "copy@example.invalid", "Secret123", None
    )
    login()

    response = client.post(
        f"/api/accounts/{account.id}/copy-account",
        json={},
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert response.status_code == 200
    assert response.json["account"]["copy_count"] == 1
    assert response.json["account"]["email_copy_count"] == 1


def test_copy_password_increments_password_copy_count(client, login, db_conn):
    account = AccountRepository(db_conn).create_pending(
        "password-copy@example.invalid", "Secret123", None
    )
    login()

    response = client.post(
        f"/api/accounts/{account.id}/copy-password",
        json={},
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert response.status_code == 200
    assert response.json["account"]["password_copy_count"] == 1


def test_bucket_filter_used_requires_email_and_password_copies(client, login, db_conn):
    repo = AccountRepository(db_conn)
    used = repo.create_pending("used@example.invalid", "Secret123", None)
    unused = repo.create_pending("unused@example.invalid", "Secret123", None)
    repo.mark_success(used.id)
    repo.mark_success(unused.id)
    repo.increment_credential_copy_count(used.id, "email")
    repo.increment_credential_copy_count(used.id, "password")
    repo.increment_credential_copy_count(unused.id, "email")
    login()

    used_response = client.get("/api/accounts?bucket=used")
    unused_response = client.get("/api/accounts?bucket=unused")

    assert used_response.status_code == 200
    assert [item["email"] for item in used_response.json["items"]] == ["used@example.invalid"]
    assert unused_response.status_code == 200
    assert [item["email"] for item in unused_response.json["items"]] == ["unused@example.invalid"]


def test_account_becomes_used_after_email_and_password_copy(client, login, db_conn):
    repo = AccountRepository(db_conn)
    account = repo.create_pending("used-after-copy@example.invalid", "Secret123", None)
    repo.mark_success(account.id)
    repo.increment_credential_copy_count(account.id, "email")
    repo.increment_credential_copy_count(account.id, "password")
    login()

    response = client.get(f"/api/accounts/{account.id}")

    assert response.status_code == 200
    assert response.json["account"]["status"] == "used"
    assert response.json["account"]["bucket"] == "used"


def test_bucket_filter_failed_returns_failed_accounts(client, login, db_conn):
    repo = AccountRepository(db_conn)
    failed = repo.create_pending("failed-route@example.invalid", "Secret123", None)
    pending = repo.create_pending("pending-route@example.invalid", "Secret123", None)
    repo.mark_failed(failed.id, "error.registration.unknown")
    login()

    response = client.get("/api/accounts?bucket=failed")

    assert response.status_code == 200
    assert [item["email"] for item in response.json["items"]] == [
        "failed-route@example.invalid"
    ]


def test_failed_page_uses_failed_bucket(client, login, db_conn):
    repo = AccountRepository(db_conn)
    failed = repo.create_pending("failed-page@example.invalid", "Secret123", None)
    pending = repo.create_pending("pending-page@example.invalid", "Secret123", None)
    repo.mark_failed(failed.id, "error.registration.unknown")
    login()

    response = client.get("/?bucket=failed")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "failed-page@example.invalid" in html
    assert "pending-page@example.invalid" not in html


def test_missing_csrf_returns_400(client, login):
    login()

    response = client.post("/api/register", json={})

    assert response.status_code == 400
    assert response.json["error"] == "error.csrf.invalid"


def test_locale_rejects_unsupported_language(client):
    client.get("/login")

    response = client.post(
        "/locale",
        json={"locale": "fr"},
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert response.status_code == 400
    assert response.json["error"] == "error.locale.unsupported"
