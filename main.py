from register import Register
from flask import Flask, render_template_string, jsonify
import pages
from util import Util
from mail import Mail

app = Flask(__name__)

@app.get("/")
def first():
    return render_template_string(pages.first_page)

@app.post("/register")
def register():
    util = Util()
    mailAddr = util.getEmail()
    print("生成邮箱: " + mailAddr)

    reg = Register()
    print("获取注册链接")
    reg.sendRegisterMail(mailAddr)

    mail = Mail(mailAddr)
    print("开始尝试注册")
    registerURL = mail.getRegisterLink()

    passwd = "Ma252525"
    if reg.registerStart(registerURL, passwd):
        print("完成注册")
    return jsonify(account=mailAddr, password="Ma252525")

if __name__ == "__main__":
    app.run()