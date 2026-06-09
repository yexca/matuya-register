# 阶段 05：Matuya 与 Gmail 外部客户端

## 阶段目标

把旧版 `Register` 和 `Mail` 中已验证的外部交互行为抽离为可测试、可替换的 client。此阶段完成后，Matuya 表单交互和 Gmail IMAP 读取可以通过 fixture 或 mock 离线测试。

## 前置输入

- 旧版 `matuya-register/register.py`
- 旧版 `matuya-register/mail.py`
- `detail_design/detailed-design.md` 第 11、12、22.6 章。

## 产出文件

```text
app/matuya/exceptions.py
app/matuya/parser.py
app/matuya/client.py
app/mail/exceptions.py
app/mail/parser.py
app/mail/imap_client.py
tests/fixtures/
```

## 开发任务

1. 定义 Matuya 异常：

```python
MatuyaError
MatuyaRequestError
MatuyaFormParseError
MatuyaSubmitError
```

2. 实现 `extract_hidden_fields(html)`：

- 使用 BeautifulSoup。
- 找不到 `<form>` 时抛 `MatuyaFormParseError`。
- 没有 hidden input 时抛 `MatuyaFormParseError`。
- 返回 `{name: value}`。

3. 实现 `MatuyaClient`：

```python
send_register_mail(email)
complete_registration(register_url, profile)
```

4. `send_register_mail` 流程：

- `GET MATUYA_REGISTER_URL`
- 解析 hidden fields
- 加入 `mail` 和 `submit=Send mail`
- `POST MATUYA_FORM_URL`
- 所有请求设置 `timeout`
- HTTP 异常映射为 `MatuyaRequestError` 或 `MatuyaSubmitError`

5. `complete_registration` 流程：

- `GET` 邮件中的注册链接。
- 解析 hidden fields。
- 填入密码、姓名、假名、电话、`mail_flag=0`、`submit=Confirm`。
- `POST MATUYA_FORM_URL` 提交确认。
- 解析确认页 hidden fields。
- 填入 `submit=Register`。
- 再次 `POST MATUYA_FORM_URL` 完成注册。

6. 定义 Mail 异常：

```python
MailError
MailLoginError
MailSearchError
MailFetchError
MailParseError
MailTimeoutError
```

7. 实现邮件 parser：

- `extract_bodies(msg)` 提取 text/plain 和 text/html。
- 跳过附件。
- charset 缺失时用 UTF-8。
- charset 不合法时 fallback 到 UTF-8。
- `extract_register_link(text, html)` 优先从纯文本提取 URL，再从 HTML 提取。

8. 实现 `MailClient.wait_register_link(recipient)`：

- SSL 连接 IMAP。
- 登录并 readonly 选择 INBOX。
- 按 `TO` 或 `CC` 搜索收件人。
- 取最新 `max_results` 封，从新到旧遍历。
- 轮询直到 `REGISTER_MAX_WAIT_SECONDS`。
- 每轮间隔 `REGISTER_POLL_INTERVAL_SECONDS`。
- 超时抛 `MailTimeoutError`。

## 保留旧版行为

- Matuya hidden fields 的解析方式继承旧版。
- 邮件 URL 提取仍以正文第一个 HTTP URL 为 MVP 策略。
- 最终注册成功判断 MVP 以 POST 无异常为准，不强依赖成功页文案。

## 新增约束

- 所有 HTTP 请求必须有 timeout。
- IMAP 轮询必须有最大等待时间。
- client 初始化不访问外部网络。
- 自动测试不得真实登录 Gmail 或访问目标站点。

## 验收标准

- fixture HTML 能提取 hidden fields。
- 无 form 或无 hidden 时会抛出明确异常。
- 纯文本邮件和 HTML 邮件均能解析注册链接。
- 无 URL 邮件抛 `MailParseError`。
- fake IMAP 超时时抛 `MailTimeoutError`。
- mock HTTP 可验证 Matuya 两段提交 payload 字段完整。
