import json
from pathlib import Path

from flask import Blueprint, current_app, redirect, request, session, url_for


bp = Blueprint("i18n", __name__)


class I18n:
    def __init__(self, locales_path, supported_locales, default_locale):
        self.supported_locales = tuple(supported_locales)
        self.default_locale = default_locale
        self.catalogs = {
            locale: self._load_catalog(Path(locales_path) / f"{locale}.json")
            for locale in self.supported_locales
        }
        self._validate_catalogs()

    def resolve_locale(self, req, user_session):
        candidates = [
            req.args.get("locale"),
            user_session.get("locale"),
            req.headers.get("Accept-Language"),
            self.default_locale,
        ]
        for candidate in candidates:
            locale = self.normalize(candidate)
            if locale in self.supported_locales:
                return locale
        return self.default_locale

    def normalize(self, value):
        if not value:
            return None
        for item in str(value).split(","):
            code = item.split(";")[0].strip()
            lower = code.lower()
            if lower in {"zh", "zh-cn", "zh-hans"}:
                return "zh-CN"
            if lower == "en" or lower.startswith("en-"):
                return "en"
        return None

    def t(self, key, locale=None, **kwargs):
        locale = locale or current_locale()
        text = self.catalogs.get(locale, {}).get(key)
        if text is None:
            text = self.catalogs[self.default_locale].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def _load_catalog(self, path):
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _validate_catalogs(self):
        expected = None
        for locale, catalog in self.catalogs.items():
            keys = set(catalog)
            if expected is None:
                expected = keys
            elif keys != expected:
                missing = sorted(expected - keys)
                extra = sorted(keys - expected)
                raise ValueError(
                    f"Locale {locale} has inconsistent keys: missing={missing}, extra={extra}"
                )


def init_i18n(app):
    config = app.config["APP_CONFIG"]
    app.extensions["i18n"] = I18n(
        Path(app.root_path) / "locales",
        config.supported_locales,
        config.default_locale,
    )

    @app.before_request
    def resolve_request_locale():
        locale = current_i18n().resolve_locale(request, session)
        request.locale = locale
        if request.args.get("locale"):
            session["locale"] = locale

    @app.context_processor
    def inject_i18n():
        i18n_obj = current_i18n()
        locale = current_locale()
        return {
            "locale": locale,
            "supported_locales": i18n_obj.supported_locales,
            "t": i18n_obj.t,
            "i18n_catalog": i18n_obj.catalogs[locale],
        }

    app.register_blueprint(bp)


def current_i18n():
    return current_app.extensions["i18n"]


def current_locale():
    return getattr(request, "locale", current_app.config["APP_CONFIG"].default_locale)


def t(key, **kwargs):
    return current_i18n().t(key, **kwargs)


def json_error(error, status=400, **kwargs):
    return {"error": error, "message": t(error, **kwargs)}, status


@bp.post("/locale")
def set_locale():
    payload = request.get_json(silent=True) or request.form
    locale = current_i18n().normalize(payload.get("locale"))
    if locale not in current_i18n().supported_locales:
        return json_error("error.locale.unsupported", 400)
    session["locale"] = locale
    if request.is_json:
        return {"locale": locale}
    return redirect(request.referrer or url_for("accounts.index"))
