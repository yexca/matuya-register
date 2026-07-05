from types import SimpleNamespace

from app.mail.mail_tm_client import MailTmClient


def test_mail_tm_client_uses_configured_suffix_without_domain_lookup():
    config = SimpleNamespace(
        mail_tm_api_base="https://mail-api.example.invalid",
        mail_tm_suffix="@mail-domain.example.invalid",
        http_timeout_seconds=1,
    )
    client = MailTmClient(config)

    assert client.domain() == "mail-domain.example.invalid"
    assert client.suffix() == "@mail-domain.example.invalid"
