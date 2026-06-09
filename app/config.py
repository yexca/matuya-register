from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    app_secret_key: str = "dev-secret-key"
    sqlite_path: str = ":memory:"
    default_locale: str = "en"
    supported_locales: tuple[str, ...] = ("en", "zh-CN")

    def to_flask_config(self) -> dict[str, object]:
        return {
            "SECRET_KEY": self.app_secret_key,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
            "SESSION_COOKIE_SECURE": False,
        }


def load_config() -> AppConfig:
    supported = tuple(
        item.strip()
        for item in os.environ.get("SUPPORTED_LOCALES", "en,zh-CN").split(",")
        if item.strip()
    )
    return AppConfig(
        app_secret_key=os.environ.get("APP_SECRET_KEY", "dev-secret-key"),
        sqlite_path=os.environ.get("SQLITE_PATH", ":memory:"),
        default_locale=os.environ.get("DEFAULT_LOCALE", "en"),
        supported_locales=supported or ("en", "zh-CN"),
    )
