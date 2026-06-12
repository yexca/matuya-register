from datetime import timedelta

from app.auth.service import AuthService


def test_initial_admin_is_created_with_hash(db_conn):
    user = AuthService(db_conn).login("admin", "password")

    assert user is not None
    assert user.password_hash != "password"
    assert user.password_hash.startswith("pbkdf2:")


def test_login_success_failure_and_logout(client, login, app):
    bad = login(password="bad-password")
    assert bad.status_code == 401

    good = login()
    assert good.status_code == 302

    with client.session_transaction() as session:
        token = session.get("csrf_token")
        assert session.permanent is True
    assert app.permanent_session_lifetime == timedelta(days=30)
    logout = client.post("/logout", data={"_csrf_token": token})
    assert logout.status_code == 302
    assert client.get("/").status_code == 302


def test_unauthenticated_page_redirects_and_api_returns_401(client):
    page = client.get("/")
    assert page.status_code == 302
    assert "/login" in page.location

    api = client.get("/api/accounts")
    assert api.status_code == 401
    assert api.json["error"] == "error.auth.required"
