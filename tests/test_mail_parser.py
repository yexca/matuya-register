from email.message import EmailMessage

import pytest

from app.mail.exceptions import MailParseError
from app.mail.parser import extract_bodies, extract_register_link


def test_extract_register_link_from_text_and_html(fixture_text):
    expected = "https://example.invalid/register/complete?token=abc123"

    assert extract_register_link(fixture_text("register_mail_text.txt")) == expected
    assert extract_register_link("", fixture_text("register_mail_html.html")) == expected


def test_extract_register_link_raises_without_url():
    with pytest.raises(MailParseError):
        extract_register_link("hello", "<p>no link</p>")


def test_extract_bodies_skips_multipart_attachments():
    message = EmailMessage()
    message.set_content("Plain body https://example.invalid/plain")
    message.add_alternative("<p>Html body</p>", subtype="html")
    message.add_attachment(
        b"https://example.invalid/attachment",
        maintype="text",
        subtype="plain",
        filename="link.txt",
    )

    text, html = extract_bodies(message)

    assert "Plain body" in text
    assert "Html body" in html
    assert "attachment" not in text
    assert "attachment" not in html
