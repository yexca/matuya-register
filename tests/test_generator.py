import re

from app.accounts.generator import AccountGenerator


def test_generator_email_password_and_profile():
    generator = AccountGenerator("@example.invalid", password_length=14)

    emails = {generator.generate_email() for _ in range(5)}
    assert len(emails) > 1
    for email in emails:
        local, suffix = email.split("@", 1)
        assert suffix == "example.invalid"
        assert re.fullmatch(r"[a-z0-9]+", local)

    password = generator.generate_password()
    assert len(password) == 14
    assert re.search(r"[a-z]", password)
    assert re.search(r"[A-Z]", password)
    assert re.search(r"\d", password)

    profile = generator.generate_profile(password)
    assert profile.password == password
    assert profile.name_sei
    assert profile.name_mei
    assert profile.kana_sei
    assert profile.kana_mei
    assert profile.phone_a in {"070", "080", "090"}
    assert re.fullmatch(r"\d{4}", profile.phone_e)
    assert re.fullmatch(r"\d{4}", profile.phone_n)
