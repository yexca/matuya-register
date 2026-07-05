from pathlib import Path

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    env = {
        "APP_SECRET_KEY": "test-secret",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "password",
        "MATUYA_REGISTER_URL": "https://example.invalid/register",
        "MATUYA_FORM_URL": "https://example.invalid/form",
        "MAIL_IMAP_HOST": "imap.example.invalid",
        "MAIL_USERNAME": "mail@example.invalid",
        "MAIL_PASSWORD": "mail-password",
        "MAIL_SUFFIX": "@example.invalid",
        "SQLITE_PATH": str(tmp_path / "app.db"),
        "BATCH_MAX_COUNT": "5",
        "BATCH_MAX_WORKERS": "2",
        "REGISTER_MAX_WAIT_SECONDS": "1",
        "REGISTER_POLL_INTERVAL_SECONDS": "1",
        "HTTP_TIMEOUT_SECONDS": "1",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    from app import create_app

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_conn(app):
    from app import db

    with app.app_context():
        yield db.get_db()


@pytest.fixture
def login(client):
    def do_login(username="admin", password="password"):
        client.get("/login")
        token = csrf_token(client)
        response = client.post(
            "/login",
            data={
                "username": username,
                "password": password,
                "_csrf_token": token,
            },
        )
        return response

    return do_login


def csrf_token(client):
    with client.session_transaction() as session:
        return session.get("csrf_token")


@pytest.fixture
def fixture_text():
    def read(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return read
