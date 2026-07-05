import hmac
import secrets
import time
from hashlib import sha256

import requests

from .exceptions import MailFetchError, MailLoginError, MailParseError, MailSearchError, MailTimeoutError
from .parser import extract_register_link


class MailTmClient:
    def __init__(
        self,
        config,
        session_factory=requests.Session,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.config = config
        self.session_factory = session_factory
        self.sleep = sleep
        self.clock = clock
        self._domains = None

    def generate_email(self):
        local = "mt" + secrets.token_hex(8)
        return f"{local}{self.suffix()}"

    def prepare_recipient(self, recipient):
        password = self._password(recipient)
        response = self._session().post(
            self._url("/accounts"),
            json={"address": recipient, "password": password},
            timeout=self.config.http_timeout_seconds,
        )
        if response.status_code not in {200, 201}:
            raise MailSearchError(f"mail.tm account creation failed: {response.status_code}")

    def wait_register_link(self, recipient):
        token = self._token(recipient)
        deadline = self.clock() + self.config.register_max_wait_seconds
        headers = self._auth_headers(token)
        session = self._session()
        while self.clock() <= deadline:
            for item in reversed(self._messages(session, headers)):
                message = self._message(session, headers, item.get("id"))
                try:
                    return extract_register_link(
                        self._body_text(message.get("text")),
                        self._body_text(message.get("html")),
                    )
                except MailParseError:
                    continue
            remaining = deadline - self.clock()
            if remaining <= 0:
                break
            self.sleep(min(self.config.register_poll_interval_seconds, remaining))
        raise MailTimeoutError(f"register mail not found for {recipient}")

    def cleanup_recipient(self, recipient):
        if not self.config.mail_tm_cleanup_account:
            return
        token_payload = self._token_payload(recipient)
        account_id = token_payload.get("id")
        if not account_id:
            return
        response = self._session().delete(
            self._url(f"/accounts/{account_id}"),
            headers=self._auth_headers(token_payload["token"]),
            timeout=self.config.http_timeout_seconds,
        )
        if response.status_code not in {200, 202, 204, 404}:
            raise MailFetchError(f"mail.tm account cleanup failed: {response.status_code}")

    def can_handle(self, recipient):
        return recipient.lower().endswith(self.config.mail_tm_suffix.lower())

    def domain(self):
        return self.config.mail_tm_suffix.lstrip("@")

    def suffix(self):
        return self.config.mail_tm_suffix

    def domains(self):
        if self._domains is None:
            response = self._session().get(
                self._url("/domains"),
                timeout=self.config.http_timeout_seconds,
            )
            if response.status_code != 200:
                raise MailSearchError(f"mail.tm domains lookup failed: {response.status_code}")
            data = response.json()
            members = data.get("hydra:member") or data.get("member") or []
            self._domains = [
                item["domain"]
                for item in members
                if item.get("domain") and item.get("isActive", True) and not item.get("isPrivate", False)
            ]
        return self._domains

    def _messages(self, session, headers):
        response = session.get(
            self._url("/messages"),
            headers=headers,
            timeout=self.config.http_timeout_seconds,
        )
        if response.status_code != 200:
            raise MailSearchError(f"mail.tm message search failed: {response.status_code}")
        data = response.json()
        return data.get("hydra:member") or data.get("member") or []

    def _message(self, session, headers, message_id):
        if not message_id:
            raise MailFetchError("mail.tm message id is missing")
        response = session.get(
            self._url(f"/messages/{message_id}"),
            headers=headers,
            timeout=self.config.http_timeout_seconds,
        )
        if response.status_code != 200:
            raise MailFetchError(f"mail.tm message fetch failed: {response.status_code}")
        return response.json()

    def _token(self, recipient):
        return self._token_payload(recipient)["token"]

    def _token_payload(self, recipient):
        response = self._session().post(
            self._url("/token"),
            json={"address": recipient, "password": self._password(recipient)},
            timeout=self.config.http_timeout_seconds,
        )
        if response.status_code != 200:
            raise MailLoginError(f"mail.tm token request failed: {response.status_code}")
        data = response.json()
        if not data.get("token"):
            raise MailLoginError("mail.tm token response did not include a token")
        return data

    def _password(self, recipient):
        digest = hmac.new(
            self.config.app_secret_key.encode("utf-8"),
            f"mail_tm:{recipient}".encode("utf-8"),
            sha256,
        ).hexdigest()
        return f"Aa1{digest}"

    def _url(self, path):
        return f"{self.config.mail_tm_api_base}{path}"

    def _session(self):
        session = self.session_factory()
        session.headers.update({"Accept": "application/ld+json, application/json"})
        return session

    def _auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _body_text(self, value):
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value)
