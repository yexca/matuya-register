from register import Register
from util import Util
from mail import Mail

def main():
    util = Util()
    mailAddr = util.getEmail()
    print("生成邮箱: " + mailAddr)

    reg = Register()
    print("获取注册链接")
    reg.sendRegisterMail(mailAddr)

    mail = Mail(mailAddr)
    print("开始尝试注册")
    registerURL = mail.getRegisterLink()

    if reg.registerStart(registerURL):
        print("完成注册")


if __name__ == "__main__":
    main()