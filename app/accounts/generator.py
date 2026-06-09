import re
import secrets
import string
from datetime import date, timedelta

from faker import Faker

from .types import RegistrationProfile


class AccountGenerator:
    def __init__(self, mail_suffix, password_length=14, faker=None):
        self.mail_suffix = mail_suffix
        self.password_length = password_length
        self.faker = faker or Faker("en_US")

    def generate_email(self):
        first_name = self.faker.first_name()
        birth_date = self._birth_date()
        token = secrets.token_hex(3)
        local = re.sub(r"[^a-z0-9]", "", f"{first_name}{birth_date}{token}".lower())
        return f"{local}{self.mail_suffix}"

    def generate_password(self):
        if self.password_length < 3:
            raise ValueError("password_length must be at least 3")
        lower = secrets.choice(string.ascii_lowercase)
        upper = secrets.choice(string.ascii_uppercase)
        digit = secrets.choice(string.digits)
        alphabet = string.ascii_letters + string.digits
        rest = [secrets.choice(alphabet) for _ in range(self.password_length - 3)]
        chars = [lower, upper, digit, *rest]
        for index in range(len(chars) - 1, 0, -1):
            swap = secrets.randbelow(index + 1)
            chars[index], chars[swap] = chars[swap], chars[index]
        return "".join(chars)

    def generate_profile(self, password):
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        return RegistrationProfile(
            password=password,
            name_sei=last_name,
            name_mei=first_name,
            kana_sei=last_name,
            kana_mei=first_name,
            phone_a=secrets.choice(("070", "080", "090")),
            phone_e=self._phone_segment(),
            phone_n=self._phone_segment(),
        )

    def _birth_date(self):
        start = date.today() - timedelta(days=365 * 40)
        end = date.today() - timedelta(days=365 * 20)
        return self.faker.date_between(start_date=start, end_date=end).strftime("%Y%m%d")

    def _phone_segment(self):
        return "".join(secrets.choice(string.digits) for _ in range(4))
