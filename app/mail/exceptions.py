class MailError(Exception):
    pass


class MailLoginError(MailError):
    pass


class MailSearchError(MailError):
    pass


class MailFetchError(MailError):
    pass


class MailParseError(MailError):
    pass


class MailTimeoutError(MailError):
    pass
