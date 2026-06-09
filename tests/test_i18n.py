import json
from pathlib import Path

from conftest import csrf_token


def test_locale_resolution_defaults_and_accept_language(app):
    client = app.test_client()
    assert b"Sign in" in client.get("/login").data

    client = app.test_client()
    response = client.get("/login", headers={"Accept-Language": "zh-CN"})
    assert "登录".encode("utf-8") in response.data

    client = app.test_client()
    response = client.get("/login", headers={"Accept-Language": "ja,en;q=0.8"})
    assert b"Sign in" in response.data


def test_locale_post_sets_session_and_rejects_unsupported(client):
    client.get("/login")
    token = csrf_token(client)

    response = client.post(
        "/locale", json={"locale": "zh-CN"}, headers={"X-CSRF-Token": token}
    )
    assert response.status_code == 200
    assert response.json == {"locale": "zh-CN"}
    assert "登录".encode("utf-8") in client.get("/login").data

    response = client.post(
        "/locale", json={"locale": "ja"}, headers={"X-CSRF-Token": token}
    )
    assert response.status_code == 400
    assert response.json["error"] == "error.locale.unsupported"


def test_locale_catalog_keys_match():
    locales_path = Path(__file__).parent.parent / "app" / "locales"
    en = set(json.loads((locales_path / "en.json").read_text()).keys())
    zh = set(json.loads((locales_path / "zh-CN.json").read_text()).keys())
    assert en == zh


def test_api_error_is_localized(client):
    response = client.get("/api/accounts", headers={"Accept-Language": "zh-CN"})
    assert response.status_code == 401
    assert response.json == {"error": "error.auth.required", "message": "需要先登录。"}
