# 阶段 08：测试与质量门槛

## 阶段目标

补齐 MVP 的离线测试，确保生成器、Repository、认证、i18n、parser、service 和路由在不访问外部网络的情况下可验证。此阶段是进入 Docker 和真实链路验证前的质量门槛。

## 前置输入

- `high_design/high-level-design.md` 第 14 章。
- `detail_design/detailed-design.md` 第 22 章。
- 阶段 01 至 07 已完成主要模块。

## 产出文件

```text
tests/conftest.py
tests/fixtures/matuya_entry.html
tests/fixtures/matuya_confirm.html
tests/fixtures/register_mail_text.txt
tests/fixtures/register_mail_html.html
tests/test_account_repository.py
tests/test_auth.py
tests/test_generator.py
tests/test_i18n.py
tests/test_mail_parser.py
tests/test_matuya_parser.py
tests/test_service.py
tests/test_routes.py
```

## 开发任务

1. `tests/conftest.py`：

- 使用临时 SQLite 文件。
- 设置测试环境变量。
- 创建 Flask test client。
- 禁用或显式控制 CSRF。
- 使用 fake client 替代真实 Gmail 和 Matuya。

2. Generator 测试：

- 邮箱以 `MAIL_SUFFIX` 结尾。
- 本地部分只包含字母数字。
- 多次生成包含随机片段。
- 密码长度正确。
- 密码至少包含小写字母、大写字母和数字。
- 注册资料字段完整，电话分段格式正确。

3. Repository 测试：

- 创建 pending 记录成功。
- 重复 email 触发唯一冲突。
- `mark_running` 设置 `started_at`。
- `mark_success` 设置 `completed_at`。
- `mark_failed` 保存错误 key。
- `list` 支持状态筛选和分页。
- `increment_copy_count` 连续调用后计数正确。

4. Auth 测试：

- 初始管理员创建。
- 管理员密码保存为 hash。
- 正确密码登录成功。
- 错误密码登录失败。
- 未登录页面跳转。
- 未登录 API 返回 `401`。
- 登出后无法访问后台。

5. i18n 测试：

- 默认语言为英语。
- `Accept-Language: zh-CN` 选择简中。
- `Accept-Language: ja,en;q=0.8` 回落英语。
- `/locale` 能写入 Session。
- 英中 JSON key 集合一致。
- API 错误包含 `error` 和本地化 `message`。

6. Parser 测试：

- Matuya fixture 能提取 hidden fields。
- 无 form 抛 `MatuyaFormParseError`。
- form 无 hidden 抛 `MatuyaFormParseError`。
- 纯文本邮件能提取 URL。
- HTML 邮件能提取 URL。
- 无 URL 抛 `MailParseError`。
- multipart 附件被跳过。

7. Service 测试：

- fake 成功路径：pending -> running -> success。
- fake Matuya 失败：failed，错误 key 正确。
- fake Mail 超时：failed，错误 key 正确。
- 邮箱冲突后重试成功。
- 邮箱冲突重试耗尽后返回错误。

8. Route 测试：

- `POST /api/register` 返回 `202`。
- `POST /api/register-batch` 校验 count。
- `GET /api/accounts` 返回分页结构。
- `GET /api/accounts/<id>` 不存在返回 `404`。
- `POST /api/accounts/<id>/copy-account` 递增复制次数。
- 缺少 CSRF 返回 `400`。
- `/locale` 拒绝不支持的语言。

## 测试边界

- 自动测试不访问真实 Matuya。
- 自动测试不登录真实 Gmail。
- 自动测试不依赖邮件实际到达。
- 真实链路验证放到阶段 10。

## 验收标准

- `pytest` 全部通过。
- 测试运行过程中无真实外部网络依赖。
- 失败路径覆盖注册流程中的主要异常。
- Repository 测试能证明唯一约束、状态更新和复制计数持久化。
- i18n 资源缺 key 会导致测试失败。
