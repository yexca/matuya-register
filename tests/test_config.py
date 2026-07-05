import pytest

from app.config import ConfigError, load_config


BASE_ENV = {
    "APP_SECRET_KEY": "test-secret",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "password",
    "MATUYA_REGISTER_URL": "https://example.invalid/register",
    "MATUYA_FORM_URL": "https://example.invalid/form",
}


def set_base_env(monkeypatch):
    for name in (
        "MAIL_PROVIDER",
        "MAIL_PROVIDER_FALLBACK",
        "MAIL_IMAP_HOST",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_SUFFIX",
        "MAIL_TM_API_BASE",
        "MAIL_TM_SUFFIX",
    ):
        monkeypatch.delenv(name, raising=False)
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)


def test_mail_tm_config_does_not_require_gmail_settings(monkeypatch):
    set_base_env(monkeypatch)
    monkeypatch.setenv("MAIL_PROVIDER", "mail_tm")
    monkeypatch.setenv("MAIL_TM_API_BASE", "https://mail-api.example.invalid")
    monkeypatch.setenv("MAIL_TM_SUFFIX", "@mail-domain.example.invalid")

    config = load_config()

    assert config.mail_providers == ("mail_tm",)
    assert config.mail_username == ""
    assert config.mail_password == ""
    assert config.mail_suffix == ""
    assert config.mail_tm_api_base == "https://mail-api.example.invalid"
    assert config.mail_tm_suffix == "@mail-domain.example.invalid"


def test_mail_provider_fallback_order(monkeypatch):
    set_base_env(monkeypatch)
    monkeypatch.setenv("MAIL_PROVIDER", "mail_tm")
    monkeypatch.setenv("MAIL_PROVIDER_FALLBACK", "gmail_imap")
    monkeypatch.setenv("MAIL_TM_API_BASE", "https://mail-api.example.invalid")
    monkeypatch.setenv("MAIL_TM_SUFFIX", "@mail-domain.example.invalid")
    monkeypatch.setenv("MAIL_IMAP_HOST", "imap.example.invalid")
    monkeypatch.setenv("MAIL_USERNAME", "mail@example.invalid")
    monkeypatch.setenv("MAIL_PASSWORD", "mail-password")
    monkeypatch.setenv("MAIL_SUFFIX", "@example.invalid")

    config = load_config()

    assert config.mail_providers == ("mail_tm", "gmail_imap")
    assert config.mail_tm_suffix == "@mail-domain.example.invalid"


def test_mail_tm_requires_configured_api_base(monkeypatch):
    set_base_env(monkeypatch)
    monkeypatch.setenv("MAIL_PROVIDER", "mail_tm")
    monkeypatch.setenv("MAIL_TM_SUFFIX", "@mail-domain.example.invalid")

    with pytest.raises(ConfigError, match="MAIL_TM_API_BASE"):
        load_config()


def test_mail_tm_requires_configured_suffix(monkeypatch):
    set_base_env(monkeypatch)
    monkeypatch.setenv("MAIL_PROVIDER", "mail_tm")
    monkeypatch.setenv("MAIL_TM_API_BASE", "https://mail-api.example.invalid")

    with pytest.raises(ConfigError, match="MAIL_TM_SUFFIX"):
        load_config()
