from faker import Faker
from datetime import datetime
import random
import config

class Util:
    def __init__(self):
        self.faker = Faker()

    def getEmail(self):
        subYear = random.randint(20, 40)
        today = datetime.today()
        birthDate = today.replace(year = today.year - subYear)
        return self.faker.first_name() + birthDate.strftime("%Y%m%d") + config.mail_suffix

    def getFirstName(self):
        return self.faker.first_name()

    def getLastName(self):
        return self.faker.last_name()
    
    def getPhonePrefix(self):
        i = ["070", "080", "090"]
        return random.choice(i)
    
    def getPhone(self):
        return ''.join(random.choice("0123456789") for _ in range(4))
