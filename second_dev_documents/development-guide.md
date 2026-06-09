# 二次开发指南

## 本地环境

推荐使用 Python 3.12，与 Docker 镜像一致。

```bash
cd matuya-register
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

本地启动：

```bash
export $(grep -v '^#' .env | xargs)
flask --app wsgi run --host 127.0.0.1 --port 8926
```

运行测试：

```bash
python -m pytest -q
```

## 代码约定

- 新业务流程优先放在 `app/accounts/service.py` 或独立 service。
- 新 SQL 只放在 repository 或迁移文件中。
- 新外部服务调用应封装成 client，便于 mock。
- 路由函数只做入参解析、权限、响应和模板渲染。
- 页面动态文案必须加入 `app/locales/en.json` 和 `app/locales/zh-CN.json`，两份 key 必须一致。
- 新 POST API 默认走 CSRF，前端通过 `X-CSRF-Token` 发送。
- 不要在 import 阶段访问 Gmail、Matuya 或数据库外部路径。

## 常见扩展点

### 增加账号字段

1. 新增迁移文件，例如 `migrations/002_add_xxx.sql`。
2. 修改 `Account` dataclass。
3. 修改 `AccountRepository._to_account()`。
4. 修改列表查询或写入方法。
5. 修改 `serialize_account()` 返回字段。
6. 如需展示，更新 `accounts.html`、`account_rows.html` 和 `app.js`。
7. 补充 repository、routes 测试。

不要直接修改已上线环境执行过的 `001_init.sql` 来变更生产表结构。应新增迁移文件。

### 增加注册阶段

注册阶段由 `AccountService._run_registration()` 控制。增加阶段时建议：

1. 将阶段逻辑封装在 generator、client 或独立 helper 中。
2. 通过 `_stage(account, "stage_name", fn, *args)` 调用，以保留统一日志。
3. 新异常类型在 `normalize_registration_error()` 中映射为稳定错误 key。
4. 在两份 locale JSON 中加入错误文案。
5. 使用 fake client 覆盖成功和失败路径。

### 支持失败重试

当前 `AccountRepository.mark_running()` 已允许 `failed -> running`，但 UI 和 API 尚未暴露重试。

建议新增：

- `POST /api/accounts/<id>/retry`
- Service 方法 `retry_registration(account_id)`
- 只允许 `failed` 状态重试
- 重试前清理 `error_message`、`completed_at`
- 前端复用现有轮询逻辑

### 替换任务执行器

当前 `TaskRunner` 是进程内线程池。它简单轻量，但进程重启会中断任务。

如需更可靠的后台任务，可引入外部队列：

- 保持 `AccountService.enqueue_*` 的对外语义不变。
- 将 `TaskRunner.submit()` 替换为队列投递。
- worker 进程独立调用 `AccountService.run_registration(account_id)`。
- 确保 worker 使用自己的 SQLite 连接。
- 增加任务幂等和重复执行保护。

### 替换邮件服务

`MailClient.wait_register_link(recipient)` 是当前 service 依赖的最小接口。替换 Gmail IMAP 时，只需保证新 client 提供同名方法并返回注册链接。

建议保留异常语义：

- 登录失败映射到 `MailLoginError`
- 搜索或抓取失败映射到 `MailSearchError` / `MailFetchError`
- 未找到链接映射到 `MailParseError`
- 等待超时映射到 `MailTimeoutError`

### 适配 Matuya 表单变更

表单字段集中在 `app/matuya/client.py`：

- 发送邮箱阶段：`mail`、`submit=Send mail`
- 确认阶段：`password`、`password:cf`、姓名、假名、电话、`mail_flag`
- 最终阶段：`submit=Register`

如果目标页面变更：

1. 先更新 fixtures 中的 HTML。
2. 调整 `extract_hidden_fields()` 或 `MatuyaClient` payload。
3. 更新 parser 和 client 测试。
4. 使用授权环境做人工验收。

## i18n 开发

语言选择优先级：

```text
query locale -> session locale -> Accept-Language -> DEFAULT_LOCALE
```

支持归一化：

- `zh`、`zh-CN`、`zh-Hans` -> `zh-CN`
- `en`、`en-US` 等 -> `en`

新增文案时必须同时修改：

```text
app/locales/en.json
app/locales/zh-CN.json
```

测试 `test_locale_catalog_keys_match` 会确保 key 集合一致。

## 错误处理

API 错误响应格式：

```json
{
  "error": "error.registration.mail_timeout",
  "message": "Registration email did not arrive in time."
}
```

数据库中的 `error_message` 保存稳定 key，不保存本地化文案。页面和 API 序列化时再按当前语言翻译。

新增错误时：

1. 定义或复用异常类型。
2. 在 `normalize_registration_error()` 映射。
3. 在 `en.json` 和 `zh-CN.json` 加文案。
4. 补测试。

## 数据一致性

- 邮箱唯一性依赖 `matuya_accounts.email` 唯一约束。
- 生成邮箱后先创建 `pending` 记录；唯一冲突时最多重试 10 次。
- 复制次数使用 SQL `copy_count = copy_count + 1` 原子递增。
- 后台线程不能复用请求上下文中的 SQLite 连接。
- 应用启动时会把遗留 `running` 标为 `error.registration.interrupted`。

