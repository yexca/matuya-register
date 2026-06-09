# 阶段 02：配置、数据库与迁移

## 阶段目标

完成环境变量配置读取、SQLite 连接管理、幂等迁移、初始管理员创建和异常启动校验。此阶段让应用拥有稳定的数据基础。

## 前置输入

- `requirement/requirements-analysis.md` 第 4.7、5.3 节。
- `detail_design/detailed-design.md` 第 4、5、7、21 章。

## 产出文件

```text
app/config.py
app/db.py
app/auth/repository.py
app/auth/service.py
migrations/001_init.sql
.env.example
```

## 开发任务

1. 在 `app/config.py` 定义 `AppConfig` 和 `load_config()`。
2. 从环境变量读取以下配置：

```text
APP_SECRET_KEY
ADMIN_USERNAME
ADMIN_PASSWORD
SQLITE_PATH
MATUYA_REGISTER_URL
MATUYA_FORM_URL
MAIL_IMAP_HOST
MAIL_IMAP_PORT
MAIL_USERNAME
MAIL_PASSWORD
MAIL_SUFFIX
REGISTER_MAX_WAIT_SECONDS
REGISTER_POLL_INTERVAL_SECONDS
HTTP_TIMEOUT_SECONDS
BATCH_MAX_COUNT
BATCH_MAX_WORKERS
PAGE_SIZE_DEFAULT
PAGE_SIZE_MAX
ENABLE_CSRF
DEFAULT_LOCALE
SUPPORTED_LOCALES
```

3. 实现配置校验：

- 必填项为空则启动失败。
- 数字项必须为合法整数。
- `MAIL_SUFFIX` 必须以 `@` 开头。
- `BATCH_MAX_COUNT` 限制在 `1..50`。
- `BATCH_MAX_WORKERS` 限制在 `1..10`。
- `PAGE_SIZE_DEFAULT` 不得超过 `PAGE_SIZE_MAX`。
- `DEFAULT_LOCALE` 必须在 `SUPPORTED_LOCALES` 中。
- MVP 只允许 `en` 和 `zh-CN`。

4. 在 `app/db.py` 中实现：

```python
init_app(app)
connect_db(sqlite_path)
get_db()
close_db(exc=None)
transaction()
run_migrations(db)
utc_now_iso()
```

5. SQLite 连接要求：

- `row_factory = sqlite3.Row`
- `pragma foreign_keys = on`
- `pragma busy_timeout = 30000`
- 初始化时启用 `pragma journal_mode = wal`
- 后台线程不能复用请求连接

6. 创建 `migrations/001_init.sql`，包含：

- `schema_migrations`
- `users`
- `matuya_accounts`
- `idx_matuya_accounts_status`
- `idx_matuya_accounts_created_at`
- `idx_matuya_accounts_created_by`

7. 实现初始管理员逻辑：

- 首次启动根据 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 创建用户。
- 密码保存 hash，不保存明文。
- 用户名已存在时，MVP 可按环境变量更新密码 hash，方便部署同步。

8. 创建 `.env.example`，只写示例值，不写真实 Gmail、Matuya 或管理员密码。

## 关键 SQL

`matuya_accounts` 必须包含唯一邮箱和状态约束：

```sql
email text not null unique,
status text not null check (status in ('pending', 'running', 'success', 'failed')),
copy_count integer not null default 0 check (copy_count >= 0)
```

## 验收标准

- 缺少必填配置时，应用启动失败并提示缺失项。
- 使用临时 SQLite 文件启动后会自动建表。
- 多次启动不会重复执行迁移。
- 管理员用户被创建，密码字段不是明文。
- `matuya_accounts.email` 具有唯一约束。
- SQLite 数据库开启 WAL、外键和 busy timeout。
