from register import Register
from flask import Flask, render_template_string, jsonify, request
from concurrent.futures import ThreadPoolExecutor, as_completed
import pages
from util import Util
from mail import Mail

app = Flask(__name__)

# @app.get("/")
# def first():
#     return render_template_string(pages.first_page)

@app.get("/")
def batch():
    return render_template_string(pages.batch_page)

# single register
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

    passwd = "Ma262626"
    if reg.registerStart(registerURL, passwd):
        print("完成注册")
    return jsonify(account=mailAddr, password=passwd)

# batch register
def process_one_register():
    """
    单个注册逻辑的封装函数
    返回字典: {success: bool, account: str, msg: str}
    """
    try:
        # 1. 生成邮箱
        util = Util()
        mailAddr = util.getEmail()
        print(f"[线程执行] 生成邮箱: {mailAddr}")

        # 2. 发送注册邮件
        reg = Register()
        # print(f"[{mailAddr}] 获取注册链接...")
        reg.sendRegisterMail(mailAddr)

        # 3. 获取注册链接 (这是最耗时的步骤之一)
        mail = Mail(mailAddr)
        # print(f"[{mailAddr}] 开始尝试获取邮件...")
        registerURL = mail.getRegisterLink()

        # 4. 提交注册
        passwd = "Ma262626" # 建议此处也可以随机生成或由参数传入
        if reg.registerStart(registerURL, passwd):
            print(f"[{mailAddr}] 完成注册")
            return {
                "success": True,
                "account": mailAddr,
                "password": passwd
            }
        else:
            return {
                "success": False,
                "account": mailAddr,
                "msg": "registerStart 返回失败"
            }

    except Exception as e:
        print(f"注册过程发生异常: {str(e)}")
        return {
            "success": False,
            "account": "unknown",
            "msg": str(e)
        }
   
@app.post("/register_batch")
def register_batch():
    # 1. 获取前端传来的参数，默认为 1
    data = request.json or {}
    count = int(data.get("count", 1))
    
    # 限制最大并发数，防止服务器崩溃或IP被封
    if count > 20: 
        return jsonify({"error": "单次请求最多支持20个并发注册"}), 400

    results = []
    
    print(f"--- 开始批量注册，目标数量: {count} ---")

    # 2. 使用线程池并发执行
    # max_workers 建议设置为 count，但不超过某个阈值（例如 10）
    worker_num = min(count, 10) 
    
    with ThreadPoolExecutor(max_workers=worker_num) as executor:
        # 提交所有任务
        futures = [executor.submit(process_one_register) for _ in range(count)]
        
        # 获取结果（as_completed 会在任务完成时立刻yield）
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # 3. 统计成功数量
    success_count = len([r for r in results if r['success']])
    
    return jsonify({
        "total_requested": count,
        "success_count": success_count,
        "details": results
    })

if __name__ == "__main__":
    app.run()