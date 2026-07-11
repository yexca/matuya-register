import os
from datetime import timedelta
from dataclasses import dataclass
from urllib.parse import urlparse


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
    mail_providers: tuple[str, ...]
    mail_imap_host: str
    mail_imap_port: int
    mail_username: str
    mail_password: str
    mail_suffix: str
    mail_tm_api_base: str
    mail_tm_suffix: str
    mail_tm_cleanup_account: bool
    register_max_wait_seconds: int
    register_poll_interval_seconds: int
    http_timeout_seconds: int
    batch_max_count: int
    batch_max_workers: int
    auto_refill_enabled: bool
    auto_refill_threshold: int
    auto_refill_target: int
    auto_refill_check_seconds: int
    auto_refill_failure_cooldown_seconds: int
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
    )
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    mail_providers = _parse_mail_providers()
    supported = _parse_locales(os.environ.get("SUPPORTED_LOCALES", "en,zh-CN"))
    default_locale = os.environ.get("DEFAULT_LOCALE", "en").strip()
    page_size_max = _env_int("PAGE_SIZE_MAX", "50")
    page_size_default = _env_int("PAGE_SIZE_DEFAULT", "20")
    batch_max_count = _env_int("BATCH_MAX_COUNT", "5")
    batch_max_workers = _env_int("BATCH_MAX_WORKERS", "2")
    mail_tm_suffix = os.environ.get("MAIL_TM_SUFFIX", "").strip()

    config = AppConfig(
        app_secret_key=_env_text("APP_SECRET_KEY"),
        admin_username=_env_text("ADMIN_USERNAME"),
        admin_password=_env_text("ADMIN_PASSWORD"),
        sqlite_path=os.environ.get("SQLITE_PATH", "/data/app.db").strip() or "/data/app.db",
        matuya_register_url=_env_text("MATUYA_REGISTER_URL"),
        matuya_form_url=_env_text("MATUYA_FORM_URL"),
        mail_providers=mail_providers,
        mail_imap_host=os.environ.get("MAIL_IMAP_HOST", "").strip(),
        mail_imap_port=_env_int("MAIL_IMAP_PORT", "993"),
        mail_username=os.environ.get("MAIL_USERNAME", "").strip(),
        mail_password=os.environ.get("MAIL_PASSWORD", "").strip(),
        mail_suffix=os.environ.get("MAIL_SUFFIX", "").strip(),
        mail_tm_api_base=os.environ.get("MAIL_TM_API_BASE", "").strip().rstrip("/"),
        mail_tm_suffix=mail_tm_suffix,
        mail_tm_cleanup_account=_env_bool("MAIL_TM_CLEANUP_ACCOUNT", False),
        register_max_wait_seconds=_env_int("REGISTER_MAX_WAIT_SECONDS", "90"),
        register_poll_interval_seconds=_env_int("REGISTER_POLL_INTERVAL_SECONDS", "5"),
        http_timeout_seconds=_env_int("HTTP_TIMEOUT_SECONDS", "20"),
        batch_max_count=batch_max_count,
        batch_max_workers=batch_max_workers,
        auto_refill_enabled=_env_bool("AUTO_REFILL_ENABLED", False),
        auto_refill_threshold=_env_int("AUTO_REFILL_THRESHOLD", "5"),
        auto_refill_target=_env_int("AUTO_REFILL_TARGET", "10"),
        auto_refill_check_seconds=_env_int("AUTO_REFILL_CHECK_SECONDS", "60"),
        auto_refill_failure_cooldown_seconds=_env_int(
            "AUTO_REFILL_FAILURE_COOLDOWN_SECONDS", "300"
        ),
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


def _parse_mail_providers() -> tuple[str, ...]:
    raw = ",".join(
        item for item in (
            os.environ.get("MAIL_PROVIDER", "gmail_imap"),
            os.environ.get("MAIL_PROVIDER_FALLBACK", ""),
        )
        if item
    )
    providers = []
    for item in raw.split(","):
        name = item.strip().lower().replace("-", "_")
        if name and name not in providers:
            providers.append(name)
    if not providers:
        raise ConfigError("MAIL_PROVIDER must not be empty")
    return tuple(providers)


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
        if "gmail_imap" in config.mail_providers or config.mail_suffix:
            raise ConfigError("MAIL_SUFFIX must start with @")
    if "gmail_imap" in config.mail_providers:
        missing = [
            name
            for name, value in {
                "MAIL_USERNAME": config.mail_username,
                "MAIL_PASSWORD": config.mail_password,
                "MAIL_SUFFIX": config.mail_suffix,
                "MAIL_IMAP_HOST": config.mail_imap_host,
            }.items()
            if not value
        ]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")
    if "mail_tm" in config.mail_providers:
        if not config.mail_tm_api_base:
            raise ConfigError("MAIL_TM_API_BASE is required when MAIL_PROVIDER includes mail_tm")
        parsed = urlparse(config.mail_tm_api_base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError("MAIL_TM_API_BASE must be an absolute HTTP URL")
        if not config.mail_tm_suffix:
            raise ConfigError("MAIL_TM_SUFFIX is required when MAIL_PROVIDER includes mail_tm")
        if not config.mail_tm_suffix.startswith("@"):
            raise ConfigError("MAIL_TM_SUFFIX must start with @")
    unknown = set(config.mail_providers) - {"gmail_imap", "mail_tm"}
    if unknown:
        raise ConfigError(f"Unsupported MAIL_PROVIDER value: {', '.join(sorted(unknown))}")
    if not 1 <= config.batch_max_count <= 50:
        raise ConfigError("BATCH_MAX_COUNT must be between 1 and 50")
    if not 1 <= config.batch_max_workers <= 10:
        raise ConfigError("BATCH_MAX_WORKERS must be between 1 and 10")
    if config.auto_refill_threshold < 1:
        raise ConfigError("AUTO_REFILL_THRESHOLD must be greater than 0")
    if config.auto_refill_target <= config.auto_refill_threshold:
        raise ConfigError("AUTO_REFILL_TARGET must be greater than AUTO_REFILL_THRESHOLD")
    if config.auto_refill_check_seconds < 1:
        raise ConfigError("AUTO_REFILL_CHECK_SECONDS must be greater than 0")
    if config.auto_refill_failure_cooldown_seconds < 0:
        raise ConfigError("AUTO_REFILL_FAILURE_COOLDOWN_SECONDS must be 0 or greater")
    if not 1 <= config.page_size_default <= config.page_size_max:
        raise ConfigError("PAGE_SIZE_DEFAULT must be between 1 and PAGE_SIZE_MAX")
    allowed = {"en", "zh-CN"}
    if set(config.supported_locales) - allowed:
        raise ConfigError("SUPPORTED_LOCALES may only contain en and zh-CN")
    if config.default_locale not in config.supported_locales:
        raise ConfigError("DEFAULT_LOCALE must be in SUPPORTED_LOCALES")
