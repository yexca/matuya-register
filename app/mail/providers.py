from app.accounts.generator import AccountGenerator

from .imap_client import MailClient
from .exceptions import MailSearchError
from .mail_tm_client import MailTmClient


class GmailImapProvider:
    name = "gmail_imap"

    def __init__(self, config, generator=None, mail_client=None):
        self.config = config
        self.generator = generator or AccountGenerator(config.mail_suffix)
        self.mail_client = mail_client or MailClient(config)

    def generate_email(self):
        return self.generator.generate_email()

    def prepare_recipient(self, recipient):
        return None

    def wait_register_link(self, recipient):
        return self.mail_client.wait_register_link(recipient)

    def cleanup_recipient(self, recipient):
        return None

    def can_handle(self, recipient):
        return recipient.lower().endswith(self.config.mail_suffix.lower())


class MailTmProvider:
    name = "mail_tm"

    def __init__(self, config, client=None):
        self.client = client or MailTmClient(config)

    def generate_email(self):
        return self.client.generate_email()

    def prepare_recipient(self, recipient):
        return self.client.prepare_recipient(recipient)

    def wait_register_link(self, recipient):
        return self.client.wait_register_link(recipient)

    def cleanup_recipient(self, recipient):
        return self.client.cleanup_recipient(recipient)

    def can_handle(self, recipient):
        return self.client.can_handle(recipient)


class FallbackMailProvider:
    def __init__(self, providers):
        self.providers = tuple(providers)

    def wait_register_link(self, recipient):
        for provider in self.providers:
            if provider.can_handle(recipient):
                return provider.wait_register_link(recipient)
        names = ", ".join(provider.name for provider in self.providers)
        raise MailSearchError(f"no configured mail provider can handle {recipient}; tried {names}")

    def cleanup_recipient(self, recipient):
        for provider in self.providers:
            if provider.can_handle(recipient):
                return provider.cleanup_recipient(recipient)
        return None


def create_mail_provider(config, generator=None, mail_client=None):
    providers = []
    for name in config.mail_providers:
        if name == "gmail_imap":
            providers.append(GmailImapProvider(config, generator=generator, mail_client=mail_client))
        elif name == "mail_tm":
            providers.append(MailTmProvider(config))
    return FallbackMailProvider(providers)
