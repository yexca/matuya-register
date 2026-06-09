import email
import imaplib
import ssl
import time

from .exceptions import MailFetchError, MailLoginError, MailSearchError, MailTimeoutError
from .parser import extract_bodies, extract_register_link


class MailClient:
    def __init__(
        self,
        config,
        imap_factory=imaplib.IMAP4_SSL,
        sleep=time.sleep,
        clock=time.monotonic,
        max_results=20,
    ):
        self.config = config
        self.imap_factory = imap_factory
        self.sleep = sleep
        self.clock = clock
        self.max_results = max_results

    def wait_register_link(self, recipient):
        deadline = self.clock() + self.config.register_max_wait_seconds
        client = self._connect()
        try:
            while self.clock() <= deadline:
                for uid in reversed(self._search_uids(client, recipient)):
                    message = self._fetch(client, uid)
                    text, html = extract_bodies(message)
                    try:
                        return extract_register_link(text, html)
                    except Exception:
                        continue
                remaining = deadline - self.clock()
                if remaining <= 0:
                    break
                self.sleep(min(self.config.register_poll_interval_seconds, remaining))
                if hasattr(client, "noop"):
                    client.noop()
            raise MailTimeoutError(f"register mail not found for {recipient}")
        finally:
            if hasattr(client, "logout"):
                client.logout()

    def _connect(self):
        try:
            context = ssl.create_default_context()
            client = self.imap_factory(
                self.config.mail_imap_host,
                self.config.mail_imap_port,
                ssl_context=context,
            )
            client.login(self.config.mail_username, self.config.mail_password)
            client.select("INBOX", readonly=True)
            return client
        except Exception as exc:
            raise MailLoginError(str(exc)) from exc

    def _search_uids(self, client, recipient):
        typ, data = client.uid("search", None, "OR", "TO", recipient, "CC", recipient)
        if typ != "OK":
            raise MailSearchError(f"IMAP search failed: {typ}")
        ids = data[0].split() if data and data[0] else []
        return ids[-self.max_results :]

    def _fetch(self, client, uid):
        typ, data = client.uid("fetch", uid, "(BODY.PEEK[])")
        if typ != "OK" or not data or not data[0]:
            raise MailFetchError(f"IMAP fetch failed: {typ}")
        return email.message_from_bytes(data[0][1])
