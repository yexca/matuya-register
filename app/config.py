import os
from datetime import timedelta
from dataclasses import dataclass


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    app_secret_key: str
    admin_username: str
    admin_password: str
    sqlite_path: str
    matuya_register_url: str
    matuya_form_url: str
    mail_imap_host: str
    mail_imap_port: int
    mail_username: str
    mail_password: str
    mail_suffix: str
    register_max_wait_seconds: int
    register_poll_interval_seconds: int
    http_timeout_seconds: int
    batch_max_count: int
    batch_max_workers: int
    page_size_default: int
    page_size_max: int
    enable_csrf: bool
    default_locale: str
    supported_locales: tuple[str, ...]
    session_cookie_secure: bool
    session_lifetime_days: int

    def to_flask_config(self) -> dict[str, object]:
        return {
            "SECRET_KEY": self.app_secret_key,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
            "SESSION_COOKIE_SECURE": self.session_cookie_secure,
            "PERMANENT_SESSION_LIFETIME": timedelta(days=self.session_lifetime_days),
        }


def load_config() -> AppConfig:
    required = (
        "APP_SECRET_KEY",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
        "MATUYA_REGISTER_URL",
        "MATUYA_FORM_URL",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_SUFFIX",
    )
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    supported = _parse_locales(os.environ.get("SUPPORTED_LOCALES", "en,zh-CN"))
    default_locale = os.environ.get("DEFAULT_LOCALE", "en").strip()
    page_size_max = _env_int("PAGE_SIZE_MAX", "50")
    page_size_default = _env_int("PAGE_SIZE_DEFAULT", "20")
    batch_max_count = _env_int("BATCH_MAX_COUNT", "5")
    batch_max_workers = _env_int("BATCH_MAX_WORKERS", "2")

    config = AppConfig(
        app_secret_key=_env_text("APP_SECRET_KEY"),
        admin_username=_env_text("ADMIN_USERNAME"),
        admin_password=_env_text("ADMIN_PASSWORD"),
        sqlite_path=os.environ.get("SQLITE_PATH", "/data/app.db").strip() or "/data/app.db",
        matuya_register_url=_env_text("MATUYA_REGISTER_URL"),
        matuya_form_url=_env_text("MATUYA_FORM_URL"),
        mail_imap_host=os.environ.get("MAIL_IMAP_HOST", "imap.gmail.com").strip() or "imap.gmail.com",
        mail_imap_port=_env_int("MAIL_IMAP_PORT", "993"),
        mail_username=_env_text("MAIL_USERNAME"),
        mail_password=_env_text("MAIL_PASSWORD"),
        mail_suffix=_env_text("MAIL_SUFFIX"),
        register_max_wait_seconds=_env_int("REGISTER_MAX_WAIT_SECONDS", "90"),
        register_poll_interval_seconds=_env_int("REGISTER_POLL_INTERVAL_SECONDS", "5"),
        http_timeout_seconds=_env_int("HTTP_TIMEOUT_SECONDS", "20"),
        batch_max_count=batch_max_count,
        batch_max_workers=batch_max_workers,
        page_size_default=page_size_default,
        page_size_max=page_size_max,
        enable_csrf=_env_bool("ENABLE_CSRF", True),
        default_locale=default_locale,
        supported_locales=supported,
        session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", False),
        session_lifetime_days=_env_int("SESSION_LIFETIME_DAYS", "30"),
    )
    _validate(config)
    return config


def _env_text(name: str) -> str:
    return os.environ[name].strip()


def _env_int(name: str, default: str) -> int:
    raw = os.environ.get(name, default).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a valid integer") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be a boolean")


def _parse_locales(raw: str) -> tuple[str, ...]:
    locales = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not locales:
        raise ConfigError("SUPPORTED_LOCALES must not be empty")
    return locales


def _validate(config: AppConfig) -> None:
    positive = {
        "MAIL_IMAP_PORT": config.mail_imap_port,
        "REGISTER_MAX_WAIT_SECONDS": config.register_max_wait_seconds,
        "REGISTER_POLL_INTERVAL_SECONDS": config.register_poll_interval_seconds,
        "HTTP_TIMEOUT_SECONDS": config.http_timeout_seconds,
        "SESSION_LIFETIME_DAYS": config.session_lifetime_days,
    }
    for name, value in positive.items():
        if value <= 0:
            raise ConfigError(f"{name} must be greater than 0")

    if not config.mail_suffix.startswith("@"):
        raise ConfigError("MAIL_SUFFIX must start with @")
    if not 1 <= config.batch_max_count <= 50:
        raise ConfigError("BATCH_MAX_COUNT must be between 1 and 50")
    if not 1 <= config.batch_max_workers <= 10:
        raise ConfigError("BATCH_MAX_WORKERS must be between 1 and 10")
    if not 1 <= config.page_size_default <= config.page_size_max:
        raise ConfigError("PAGE_SIZE_DEFAULT must be between 1 and PAGE_SIZE_MAX")
    allowed = {"en", "zh-CN"}
    if set(config.supported_locales) - allowed:
        raise ConfigError("SUPPORTED_LOCALES may only contain en and zh-CN")
    if config.default_locale not in config.supported_locales:
        raise ConfigError("DEFAULT_LOCALE must be in SUPPORTED_LOCALES")
