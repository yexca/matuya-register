import re
from html import unescape

from bs4 import BeautifulSoup

from .exceptions import MailParseError


URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")


def extract_bodies(msg):
    text_body = ""
    html_body = ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        disposition = (part.get("Content-Disposition") or "").lower().strip()
        if disposition.startswith("attachment"):
            continue
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            decoded = payload.decode(charset, errors="ignore")
        except LookupError:
            decoded = payload.decode("utf-8", errors="ignore")
        if content_type == "text/plain":
            text_body += decoded
        elif content_type == "text/html":
            html_body += decoded
    return text_body.strip(), html_body.strip()


def extract_register_link(text, html=""):
    for source in (text or "", _html_to_text(html or ""), html or ""):
        match = URL_PATTERN.search(source)
        if match:
            return unescape(match.group(0)).rstrip(").,]")
    raise MailParseError("register link not found")


def _html_to_text(html):
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ")
