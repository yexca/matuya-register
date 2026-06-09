import requests

from .exceptions import MatuyaRequestError, MatuyaSubmitError
from .parser import extract_hidden_fields


class MatuyaClient:
    def __init__(self, config, session_factory=requests.Session):
        self.config = config
        self.session_factory = session_factory
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en,zh-CN;q=0.9,ja;q=0.8",
        }

    def send_register_mail(self, email):
        session = self.session_factory()
        try:
            response = session.get(
                self.config.matuya_register_url,
                headers=self.headers,
                allow_redirects=True,
                timeout=self.config.http_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MatuyaRequestError(str(exc)) from exc
        payload = extract_hidden_fields(response.text)
        payload.update({"mail": email, "submit": "Send mail"})
        try:
            response = session.post(
                self.config.matuya_form_url,
                data=payload,
                headers=self.headers,
                allow_redirects=True,
                timeout=self.config.http_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MatuyaSubmitError(str(exc)) from exc
        return True

    def complete_registration(self, register_url, profile):
        session = self.session_factory()
        try:
            response = session.get(
                register_url,
                headers=self.headers,
                allow_redirects=True,
                timeout=self.config.http_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MatuyaRequestError(str(exc)) from exc

        payload = extract_hidden_fields(response.text)
        payload.update(
            {
                "password": profile.password,
                "password:cf": profile.password,
                "name_mei": profile.name_mei,
                "kana_mei": profile.kana_mei,
                "name_sei": profile.name_sei,
                "kana_sei": profile.kana_sei,
                "phone:a": profile.phone_a,
                "phone:e": profile.phone_e,
                "phone:n": profile.phone_n,
                "mail_flag": "0",
                "submit": "Confirm",
            }
        )
        try:
            response = session.post(
                self.config.matuya_form_url,
                data=payload,
                headers=self.headers,
                allow_redirects=True,
                timeout=self.config.http_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MatuyaSubmitError(str(exc)) from exc

        payload = extract_hidden_fields(response.text)
        payload.update({"submit": "Register"})
        try:
            response = session.post(
                self.config.matuya_form_url,
                data=payload,
                headers=self.headers,
                allow_redirects=True,
                timeout=self.config.http_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MatuyaSubmitError(str(exc)) from exc
        return True
