import requests
from bs4 import BeautifulSoup
from util import Util

class Register:
    def __init__(self):
        self.ACTION_URL = "https://reg31.smp.ne.jp/regist/Reg2"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept-Language": "en,zh-CN;q=0.9,zh-HK;q=0.8,zh;q=0.7,ja;q=0.6"
        }
        self.util = Util()
    
    def getHiddenItem(self, soup):
        form = soup.find("form")
        payload = {}
        for inp in form.find_all("input", {"type": "hidden"}):
            if inp.get("name") and inp.get("value") is not None:
                payload[inp["name"]] = inp["value"]
        return payload

    def sendRegisterMail(self, mail):
        REGISTER_URL = "https://reg31.smp.ne.jp/regist/is?SMPFORM=liqi-lhkikb-6c3edcca6d4ae20d151a83f0478f6987"

        session = requests.Session()
        r = session.get(REGISTER_URL, headers=self.headers, allow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")

        # get hidden item
        payload = self.getHiddenItem(soup)
        payload.update({
            "mail": mail,
            "submit": "Send mail"
        })

        session.post(self.ACTION_URL, data=payload, headers=self.headers, allow_redirects=True)
        return True

    def registerStart(self, registerURL):
        session = requests.Session()

        # goto register web
        r = session.get(registerURL, headers=self.headers, allow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")

        # first get hidden
        payload = self.getHiddenItem(soup)
        sei = self.util.getLastName()
        mei = self.util.getFirstName()
        payload.update({
            "password": "Ma252525",
            "password:cf": "Ma252525",
            "name_mei": mei,
            "kana_mei": mei,
            "name_sei": sei,
            "kana_sei": sei,
            "phone:a": self.util.getPhonePrefix(),
            "phone:e": self.util.getPhone(),
            "phone:n": self.util.getPhone(),
            "mail_flag": "0",
            "submit": "Confirm"
        })
        r2 = session.post(self.ACTION_URL, data=payload, headers=self.headers, allow_redirects=True)

        # seconed
        soup2 = BeautifulSoup(r2.text, "html.parser")

        # seconed get hidden
        payload2 = self.getHiddenItem(soup2)
        payload2.update({
            "submit": "Register",
        })
        
        # complete
        session.post(self.ACTION_URL, data=payload2, headers=self.headers, allow_redirects=True)

        return True
