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


def test_get_accounts_returns_pagination(client, login, db_conn):
    AccountRepository(db_conn).create_pending("page@example.invalid", "Secret123", None)
    login()

    response = client.get("/api/accounts?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["email"] == "page@example.invalid"


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
