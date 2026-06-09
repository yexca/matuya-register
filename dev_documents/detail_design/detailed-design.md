# Matuya 注册工具升级重写详细设计

## 1. 文档目的

本文基于以下文档和旧版 `matuya-register` 代码，给出可直接指导编码、测试和部署的详细设计：

- `requirement/requirements-analysis.md`
- `high_design/high-level-design.md`
- 旧版 `matuya-register/app.py`
- 旧版 `matuya-register/register.py`
- 旧版 `matuya-register/mail.py`
- 旧版 `matuya-register/util.py`

新版本保持轻量化和单容器部署，使用 Flask、Jinja2、SQLite、`requests`、`imaplib` 和进程内线程池完成 MVP。本文不描述非法或未授权用途，系统默认提供免责声明、登录保护、并发限制和配置化能力。

## 2. 详细设计范围

本文覆盖：

- 目录结构和模块职责。
- 配置项、默认值、校验规则。
- 数据库表、迁移 SQL、Repository 方法。
- 领域对象和状态枚举。
- 登录认证流程。
- 邮箱、密码、姓名、电话生成细节。
- Matuya HTTP 表单交互流程。
- Gmail IMAP 轮询和邮件 URL 解析流程。
- 单个和批量注册任务调度。
- 后台页面与 API 请求响应。
- 简中和英语 i18n，按浏览器语言自动切换，默认英语。
- CSRF、Session、安全和日志策略。
- 测试用例拆分。
- MVP 编码顺序。

本文不覆盖：

- 多管理员权限体系。
- 分布式任务队列。
- 密码字段加密存储。
- 注册事件明细后台页面。
- 失败记录一键重试。

## 3. 目标目录结构

```text
matuya-register/
  app/
    __init__.py
    config.py
    db.py
    i18n.py
    logging.py
    security.py
    auth/
      __init__.py
      decorators.py
      repository.py
      routes.py
      service.py
    accounts/
      __init__.py
      generator.py
      repository.py
      routes.py
      service.py
      tasks.py
      types.py
    matuya/
      __init__.py
      client.py
      exceptions.py
      parser.py
      types.py
    mail/
      __init__.py
      exceptions.py
      imap_client.py
      parser.py
    templates/
      base.html
      login.html
      accounts.html
      partials/
        account_rows.html
    locales/
      en.json
      zh-CN.json
    static/
      app.css
      app.js
  migrations/
    001_init.sql
  tests/
    conftest.py
    fixtures/
      matuya_entry.html
      matuya_confirm.html
      register_mail_text.txt
      register_mail_html.html
    test_account_repository.py
    test_auth.py
    test_generator.py
    test_mail_parser.py
    test_matuya_parser.py
    test_routes.py
  wsgi.py
  requirements.txt
  Dockerfile
  docker-compose.yml
  .dockerignore
  .env.example
```

设计约束：

- 路由层不直接调用 `requests`、`imaplib` 或写 SQL。
- Service 层负责编排状态转换。
- Repository 层独占 SQL 和事务细节。
- 外部交互通过 Client 封装，便于 mock 测试。
- 启动入口只创建 app，不在模块 import 阶段连接外部服务。

## 4. 配置详细设计

### 4.1 配置对象

`app/config.py` 定义 `AppConfig`。应用启动时从环境变量构造配置对象，并挂到 `app.config["APP_CONFIG"]`。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    secret_key: str
    admin_username: str
    admin_password: str
    sqlite_path: str
    matuya_register_url: str
    matuya_form_url: str
    mail_imap_host: str
    mail_imap_port: int
    mail_username: str
    mail_password: str
    mail_suffix: str
    register_max_wait_seconds: int
    register_poll_interval_seconds: int
    http_timeout_seconds: int
    batch_max_count: int
    batch_max_workers: int
    page_size_default: int
    page_size_max: int
    enable_csrf: bool
    default_locale: str
    supported_locales: tuple[str, ...]
```

### 4.2 环境变量

| 环境变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `APP_SECRET_KEY` | 无 | 是 | Flask Session 密钥 |
| `ADMIN_USERNAME` | 无 | 是 | 初始管理员用户名 |
| `ADMIN_PASSWORD` | 无 | 是 | 初始管理员密码 |
| `SQLITE_PATH` | `/data/app.db` | 否 | SQLite 文件路径 |
| `MATUYA_REGISTER_URL` | 无 | 是 | Matuya 注册入口 |
| `MATUYA_FORM_URL` | 无 | 是 | Matuya 表单提交 URL |
| `MAIL_IMAP_HOST` | `imap.gmail.com` | 否 | IMAP Host |
| `MAIL_IMAP_PORT` | `993` | 否 | IMAP SSL 端口 |
| `MAIL_USERNAME` | 无 | 是 | Gmail 账号 |
| `MAIL_PASSWORD` | 无 | 是 | Gmail app password |
| `MAIL_SUFFIX` | 无 | 是 | 邮箱后缀，例如 `@example.com` |
| `REGISTER_MAX_WAIT_SECONDS` | `90` | 否 | 等待邮件最大秒数 |
| `REGISTER_POLL_INTERVAL_SECONDS` | `5` | 否 | 轮询间隔秒数 |
| `HTTP_TIMEOUT_SECONDS` | `20` | 否 | HTTP 请求超时 |
| `BATCH_MAX_COUNT` | `5` | 否 | 单次批量数量上限 |
| `BATCH_MAX_WORKERS` | `2` | 否 | 线程池并发上限 |
| `PAGE_SIZE_DEFAULT` | `20` | 否 | 历史列表默认分页大小 |
| `PAGE_SIZE_MAX` | `50` | 否 | API 允许的最大分页大小 |
| `ENABLE_CSRF` | `true` | 否 | 是否启用 CSRF |
| `DEFAULT_LOCALE` | `en` | 否 | 默认界面语言 |
| `SUPPORTED_LOCALES` | `en,zh-CN` | 否 | 支持的界面语言 |

### 4.3 配置校验

启动时执行校验：

- 必填项为空时抛出 `ConfigError`，应用启动失败。
- 数字项必须能转换为整数。
- `MAIL_IMAP_PORT`、`REGISTER_MAX_WAIT_SECONDS`、`REGISTER_POLL_INTERVAL_SECONDS`、`HTTP_TIMEOUT_SECONDS` 必须大于 0。
- `BATCH_MAX_COUNT` 必须在 `1..50`。
- `BATCH_MAX_WORKERS` 必须在 `1..10`，且运行时取 `min(BATCH_MAX_WORKERS, BATCH_MAX_COUNT)`。
- `PAGE_SIZE_DEFAULT` 必须在 `1..PAGE_SIZE_MAX`。
- `MAIL_SUFFIX` 必须以 `@` 开头。
- `DEFAULT_LOCALE` 必须在 `SUPPORTED_LOCALES` 中。
- MVP 只支持 `en` 和 `zh-CN`，即使环境变量包含其他值也应启动失败，避免缺少翻译资源。
- 生产部署中 `APP_SECRET_KEY` 长度建议不少于 32 字符；MVP 只警告，不阻断。

### 4.4 `.env.example`

`.env.example` 只保存示例，不保存真实密钥：

```env
APP_SECRET_KEY=change-me-to-a-long-random-string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
SQLITE_PATH=/data/app.db

MATUYA_REGISTER_URL=https://example.invalid/register
MATUYA_FORM_URL=https://example.invalid/form

MAIL_IMAP_HOST=imap.gmail.com
MAIL_IMAP_PORT=993
MAIL_USERNAME=your-gmail@example.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_SUFFIX=@example.com

REGISTER_MAX_WAIT_SECONDS=90
REGISTER_POLL_INTERVAL_SECONDS=5
HTTP_TIMEOUT_SECONDS=20
BATCH_MAX_COUNT=5
BATCH_MAX_WORKERS=2
PAGE_SIZE_DEFAULT=20
PAGE_SIZE_MAX=50
ENABLE_CSRF=true
DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en,zh-CN
```

## 5. 数据库详细设计

### 5.1 连接管理

`app/db.py` 提供：

```python
def init_app(app: Flask) -> None: ...
def get_db() -> sqlite3.Connection: ...
def close_db(exc: BaseException | None = None) -> None: ...
def transaction() -> Iterator[sqlite3.Connection]: ...
def run_migrations(db: sqlite3.Connection) -> None: ...
```

连接规则：

- Web 请求中通过 Flask `g` 保存当前连接。
- 后台线程中不能复用请求连接，必须按需新建连接。
- `sqlite3.connect(..., timeout=30, isolation_level=None)`。
- `row_factory = sqlite3.Row`。
- 每个新连接执行：

```sql
pragma foreign_keys = on;
pragma busy_timeout = 30000;
```

应用初始化迁移时执行：

```sql
pragma journal_mode = wal;
```

事务上下文：

```python
@contextmanager
def transaction():
    db = get_db()
    try:
        db.execute("begin")
        yield db
        db.execute("commit")
    except Exception:
        db.execute("rollback")
        raise
```

后台线程可使用 `connect_db(config.sqlite_path)` 创建独立连接，再传入 Repository。

### 5.2 迁移表

为保证迁移幂等，增加 `schema_migrations`：

```sql
create table if not exists schema_migrations (
  version text primary key,
  applied_at text not null
);
```

启动时按文件名排序执行 `migrations/*.sql`：

1. 查询 `schema_migrations` 是否已存在版本。
2. 未执行则在事务中执行 SQL 文件。
3. 插入版本记录。

### 5.3 初始迁移 SQL

`migrations/001_init.sql`：

```sql
create table if not exists users (
  id integer primary key,
  username text not null unique,
  password_hash text not null,
  created_at text not null,
  updated_at text not null
);

create table if not exists matuya_accounts (
  id integer primary key,
  email text not null unique,
  password text not null,
  status text not null check (status in ('pending', 'running', 'success', 'failed')),
  error_message text,
  copy_count integer not null default 0 check (copy_count >= 0),
  last_copied_at text,
  created_by integer,
  started_at text,
  completed_at text,
  created_at text not null,
  updated_at text not null,
  foreign key (created_by) references users(id)
);

create index if not exists idx_matuya_accounts_status
  on matuya_accounts(status);

create index if not exists idx_matuya_accounts_created_at
  on matuya_accounts(created_at);

create index if not exists idx_matuya_accounts_created_by
  on matuya_accounts(created_by);
```

### 5.4 时间格式

所有时间保存 UTC ISO8601 字符串：

```text
2026-06-09T03:10:45Z
```

`app/db.py` 或 `app/utils` 提供：

```python
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
```

页面展示时 MVP 直接显示 UTC，后续可按浏览器时区转换。

## 6. 领域对象和枚举

`app/accounts/types.py`：

```python
from dataclasses import dataclass
from enum import StrEnum

class AccountStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass(frozen=True)
class Account:
    id: int
    email: str
    password: str
    status: AccountStatus
    error_message: str | None
    copy_count: int
    last_copied_at: str | None
    created_by: int | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str

@dataclass(frozen=True)
class Page:
    items: list[Account]
    page: int
    page_size: int
    total: int

@dataclass(frozen=True)
class CopyResult:
    account_id: int
    copy_count: int
    last_copied_at: str

@dataclass(frozen=True)
class RegistrationResult:
    account_id: int
    status: AccountStatus
    error_message: str | None = None
```

`app/matuya/types.py`：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RegistrationProfile:
    password: str
    name_sei: str
    name_mei: str
    kana_sei: str
    kana_mei: str
    phone_a: str
    phone_e: str
    phone_n: str
```

## 7. Repository 详细设计

### 7.1 UserRepository

`app/auth/repository.py`

```python
class UserRepository:
    def __init__(self, db: sqlite3.Connection): ...
    def get_by_username(self, username: str) -> User | None: ...
    def get_by_id(self, user_id: int) -> User | None: ...
    def create(self, username: str, password_hash: str) -> User: ...
    def update_password_hash(self, user_id: int, password_hash: str) -> None: ...
```

SQL 要点：

- `get_by_username` 使用精确匹配。
- `create` 捕获唯一约束冲突，返回已存在用户或抛出业务错误。
- 初始管理员创建时，如果用户名存在但密码环境变量变化，MVP 建议更新密码哈希，方便容器重建后同步管理员密码。

### 7.2 AccountRepository

`app/accounts/repository.py`

```python
class AccountRepository:
    def __init__(self, db: sqlite3.Connection): ...
    def create_pending(self, email: str, password: str, created_by: int | None) -> Account: ...
    def get(self, account_id: int) -> Account | None: ...
    def list(self, status: str | None, page: int, page_size: int) -> Page: ...
    def mark_running(self, account_id: int) -> Account: ...
    def mark_success(self, account_id: int) -> Account: ...
    def mark_failed(self, account_id: int, error_message: str) -> Account: ...
    def increment_copy_count(self, account_id: int) -> CopyResult: ...
```

#### 7.2.1 创建 pending 记录

```sql
insert into matuya_accounts (
  email, password, status, error_message, copy_count,
  created_by, created_at, updated_at
) values (?, ?, 'pending', null, 0, ?, ?, ?);
```

唯一冲突处理：

- 捕获 `sqlite3.IntegrityError`。
- 如果错误来自 `matuya_accounts.email`，向上抛出 `DuplicateEmailError`。
- 由 Service 决定重新生成。

#### 7.2.2 状态更新

开始：

```sql
update matuya_accounts
set status = 'running',
    error_message = null,
    started_at = coalesce(started_at, ?),
    updated_at = ?
where id = ?
  and status in ('pending', 'failed');
```

成功：

```sql
update matuya_accounts
set status = 'success',
    error_message = null,
    completed_at = ?,
    updated_at = ?
where id = ?;
```

失败：

```sql
update matuya_accounts
set status = 'failed',
    error_message = ?,
    completed_at = ?,
    updated_at = ?
where id = ?;
```

失败原因最大长度：

- 数据库存储前截断到 500 字符。
- 详细异常堆栈只写日志。

#### 7.2.3 列表分页

状态为空时查询全部：

```sql
select *
from matuya_accounts
order by datetime(created_at) desc, id desc
limit ? offset ?;
```

状态存在时：

```sql
select *
from matuya_accounts
where status = ?
order by datetime(created_at) desc, id desc
limit ? offset ?;
```

总数查询：

```sql
select count(*) from matuya_accounts;
select count(*) from matuya_accounts where status = ?;
```

#### 7.2.4 复制次数原子递增

```sql
update matuya_accounts
set copy_count = copy_count + 1,
    last_copied_at = ?,
    updated_at = ?
where id = ?
returning id, copy_count, last_copied_at;
```

如果部署 SQLite 版本不支持 `returning`，使用事务内两步：

```sql
update matuya_accounts
set copy_count = copy_count + 1,
    last_copied_at = ?,
    updated_at = ?
where id = ?;

select id, copy_count, last_copied_at
from matuya_accounts
where id = ?;
```

## 8. 认证模块详细设计

### 8.1 AuthService

`app/auth/service.py`

```python
class AuthService:
    def __init__(self, user_repo: UserRepository): ...
    def ensure_initial_admin(self, username: str, password: str) -> None: ...
    def login(self, username: str, password: str) -> User | None: ...
    def get_current_user(self, user_id: int) -> User | None: ...
```

密码哈希：

- 使用 `werkzeug.security.generate_password_hash`。
- 使用 `werkzeug.security.check_password_hash`。

登录规则：

- 用户名、密码去除首尾空白。
- 用户不存在或密码错误时返回 `None`。
- 不在页面区分“用户不存在”和“密码错误”。

### 8.2 Session 设计

Session 字段：

| Key | 说明 |
| --- | --- |
| `user_id` | 当前后台用户 ID |
| `username` | 当前后台用户名 |
| `csrf_token` | 当前会话 CSRF token |
| `locale` | 用户手动选择的界面语言，可为空 |

登录成功：

```python
session.clear()
session["user_id"] = user.id
session["username"] = user.username
session["csrf_token"] = secrets.token_urlsafe(32)
```

登出：

```python
session.clear()
```

### 8.3 登录保护

`app/auth/decorators.py`

```python
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)
    return wrapped
```

### 8.4 CSRF 保护

`app/security.py`

规则：

- `GET`、`HEAD`、`OPTIONS` 不校验。
- 所有登录后的 `POST` API 校验。
- 表单提交从隐藏字段读取 `_csrf_token`。
- JSON API 从 Header `X-CSRF-Token` 读取。
- token 与 `session["csrf_token"]` 使用 `secrets.compare_digest` 比较。

失败返回：

```json
{
  "error": "csrf_failed"
}
```

HTTP 状态码：`400`。

### 8.5 i18n 支撑

认证页面和后台页面都必须走统一 i18n，不在模板中硬编码业务文案。登录前没有 Session 用户，但仍可通过浏览器语言选择界面语言。

登录相关文案示例：

| Key | 英语 | 简中 |
| --- | --- | --- |
| `auth.login_title` | `Sign in` | `登录` |
| `auth.username` | `Username` | `用户名` |
| `auth.password` | `Password` | `密码` |
| `auth.invalid_credentials` | `Invalid username or password.` | `用户名或密码错误。` |
| `auth.logout` | `Sign out` | `退出登录` |

## 9. 国际化 i18n 详细设计

### 9.1 目标

- 支持英语和简体中文。
- 默认语言为英语。
- 首次访问时根据浏览器 `Accept-Language` 自动选择。
- 浏览器语言无法匹配时使用英语。
- 用户可在页面手动切换语言，选择结果写入 Session。
- 后端 API 返回稳定错误码，同时返回当前语言下的简短 `message`。
- 前端动态文案从后端注入的翻译资源读取，不在 JavaScript 中硬编码中文或英文。

### 9.2 语言匹配规则

语言解析优先级：

1. Query 参数 `?lang=en` 或 `?lang=zh-CN`，用于手动切换后的跳转。
2. Session 中的 `locale`。
3. 浏览器 `Accept-Language`。
4. `DEFAULT_LOCALE`，默认 `en`。

浏览器语言归一化：

| 浏览器语言 | 系统语言 |
| --- | --- |
| `zh-CN` | `zh-CN` |
| `zh-Hans` | `zh-CN` |
| `zh` | `zh-CN` |
| `en` | `en` |
| `en-US` | `en` |
| 其他 | `en` |

实现函数：

```python
SUPPORTED_LOCALES = ("en", "zh-CN")
DEFAULT_LOCALE = "en"

def normalize_locale(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    lower = value.lower()
    if lower in ("zh", "zh-cn", "zh-hans", "zh-hans-cn"):
        return "zh-CN"
    if lower == "en" or lower.startswith("en-"):
        return "en"
    return None
```

`Accept-Language` 解析可使用 Flask/Werkzeug 的 `request.accept_languages`，但要先做上表归一化，保证 `zh` 能命中 `zh-CN`。

### 9.3 i18n 模块

`app/i18n.py`

```python
class I18n:
    def __init__(self, locales_dir: Path, default_locale: str, supported_locales: tuple[str, ...]): ...
    def resolve_locale(self, request: Request, session: SessionMixin) -> str: ...
    def set_locale(self, locale: str) -> None: ...
    def gettext(self, key: str, **kwargs: Any) -> str: ...
    def catalog(self, locale: str) -> dict[str, str]: ...
```

模板 helper：

```python
@app.context_processor
def inject_i18n():
    locale = i18n.resolve_locale(request, session)
    return {
        "locale": locale,
        "supported_locales": ("en", "zh-CN"),
        "t": lambda key, **kwargs: i18n.gettext(key, locale=locale, **kwargs),
        "i18n_catalog": i18n.catalog(locale),
    }
```

### 9.4 翻译资源

资源文件使用 JSON，便于后端和前端共用。

`app/locales/en.json`：

```json
{
  "app.title": "Matuya Register",
  "auth.login_title": "Sign in",
  "auth.username": "Username",
  "auth.password": "Password",
  "auth.submit": "Sign in",
  "auth.invalid_credentials": "Invalid username or password.",
  "nav.sign_out": "Sign out",
  "nav.language": "Language",
  "accounts.register_one": "Register one",
  "accounts.register_batch": "Register batch",
  "accounts.count": "Count",
  "accounts.status.all": "All",
  "accounts.status.pending": "Pending",
  "accounts.status.running": "Running",
  "accounts.status.success": "Success",
  "accounts.status.failed": "Failed",
  "accounts.email": "Email",
  "accounts.password": "Password",
  "accounts.error": "Error",
  "accounts.copy_count": "Copies",
  "accounts.copy_email": "Copy email",
  "accounts.copy_password": "Copy password",
  "accounts.copied": "Copied",
  "error.unauthorized": "Please sign in.",
  "error.csrf_failed": "The request expired. Please refresh and try again.",
  "error.validation_failed": "Please check your input.",
  "error.not_found": "Record not found.",
  "error.registration.config_missing": "System configuration is missing. Please check environment variables.",
  "error.registration.mail_login_failed": "Mail service login failed.",
  "error.registration.mail_timeout": "No registration link was received before timeout.",
  "error.registration.mail_parse_failed": "No registration link was found in the email.",
  "error.registration.matuya_request_failed": "Could not access the registration site.",
  "error.registration.matuya_form_changed": "The registration page structure may have changed.",
  "error.registration.matuya_submit_failed": "Registration submission failed.",
  "error.registration.email_conflict_exhausted": "Email generation conflicted too many times. Please try again later.",
  "error.registration.interrupted": "The task was interrupted because the application restarted.",
  "error.registration.unknown": "Registration failed. Please check container logs."
}
```

`app/locales/zh-CN.json`：

```json
{
  "app.title": "Matuya 注册工具",
  "auth.login_title": "登录",
  "auth.username": "用户名",
  "auth.password": "密码",
  "auth.submit": "登录",
  "auth.invalid_credentials": "用户名或密码错误。",
  "nav.sign_out": "退出登录",
  "nav.language": "语言",
  "accounts.register_one": "注册一个",
  "accounts.register_batch": "批量注册",
  "accounts.count": "数量",
  "accounts.status.all": "全部",
  "accounts.status.pending": "等待中",
  "accounts.status.running": "注册中",
  "accounts.status.success": "成功",
  "accounts.status.failed": "失败",
  "accounts.email": "邮箱",
  "accounts.password": "密码",
  "accounts.error": "失败原因",
  "accounts.copy_count": "复制次数",
  "accounts.copy_email": "复制邮箱",
  "accounts.copy_password": "复制密码",
  "accounts.copied": "已复制",
  "error.unauthorized": "请先登录。",
  "error.csrf_failed": "请求已过期，请刷新后重试。",
  "error.validation_failed": "请检查输入内容。",
  "error.not_found": "记录不存在。",
  "error.registration.config_missing": "系统配置缺失，请检查环境变量。",
  "error.registration.mail_login_failed": "邮件服务登录失败。",
  "error.registration.mail_timeout": "未在限定时间内收到注册链接。",
  "error.registration.mail_parse_failed": "邮件中未找到注册链接。",
  "error.registration.matuya_request_failed": "注册站点访问失败。",
  "error.registration.matuya_form_changed": "注册页面结构可能已变更。",
  "error.registration.matuya_submit_failed": "注册提交失败。",
  "error.registration.email_conflict_exhausted": "邮箱生成冲突过多，请稍后重试。",
  "error.registration.interrupted": "应用重启导致任务中断。",
  "error.registration.unknown": "注册失败，请查看容器日志。"
}
```

资源要求：

- `en.json` 是主资源，新增 key 必须先加英语。
- `zh-CN.json` 必须包含与 `en.json` 完全相同的 key。
- 启动时校验两份资源 key 集合一致，缺失则启动失败。
- `gettext` 找不到 key 时返回 key 本身，并记录 warning。

### 9.5 语言切换路由

新增路由：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/locale` | 手动切换界面语言 |

请求：

```json
{
  "locale": "zh-CN"
}
```

行为：

- 校验 CSRF。
- 校验语言在 `SUPPORTED_LOCALES`。
- 写入 `session["locale"]`。
- 返回当前语言。

响应：

```json
{
  "locale": "zh-CN"
}
```

页面也可以提供普通表单版语言切换，便于禁用 JavaScript 时使用：

```html
<form method="post" action="/locale">
  <input type="hidden" name="_csrf_token" value="{{ csrf_token }}">
  <button name="locale" value="en">English</button>
  <button name="locale" value="zh-CN">简体中文</button>
</form>
```

### 9.6 API 错误响应

API 错误必须同时包含稳定 `error` 和本地化 `message`。

示例：

```json
{
  "error": "csrf_failed",
  "message": "The request expired. Please refresh and try again."
}
```

简中浏览器或手动选择简中时：

```json
{
  "error": "csrf_failed",
  "message": "请求已过期，请刷新后重试。"
}
```

前端逻辑只依赖 `error` 做分支，展示使用 `message`。


## 10. 生成器详细设计

`app/accounts/generator.py`

### 10.1 AccountGenerator

```python
class AccountGenerator:
    def __init__(self, mail_suffix: str, password_length: int = 14): ...
    def generate_email(self) -> str: ...
    def generate_password(self) -> str: ...
    def generate_profile(self, password: str) -> RegistrationProfile: ...
```

### 10.2 邮箱生成

旧版策略：

- `faker.first_name() + birthDate + mail_suffix`
- 使用 `random`
- 没有数据库唯一兜底

新版策略：

1. 使用 `Faker("en_US")` 生成英文 first name。
2. 转小写，只保留字母和数字。
3. 生成年龄片段：当前年份减去 `20..40` 的随机年龄，形成 `YYYYMMDD`。
4. 使用 `secrets.token_hex(3)` 生成 6 位十六进制随机片段。
5. 拼接为 `{first_name}{birth_date}{rand}{MAIL_SUFFIX}`。

示例：

```text
alice19940609a3f91c@example.com
```

实现要点：

- 随机片段使用 `secrets`。
- 日期可使用 UTC 日期或服务器本地日期，MVP 使用 UTC 日期。
- 邮箱生成不访问数据库；唯一性由 Service 调用 Repository 插入时兜底。

### 10.3 密码生成

默认长度：14。

字符集：

```python
ascii_letters + digits
```

生成规则：

- 使用 `secrets.choice`。
- 至少包含一个小写字母、一个大写字母、一个数字。
- 不使用符号，避免目标表单兼容问题。
- 生成后打乱字符顺序。

### 10.4 姓名和电话生成

```python
def generate_profile(password: str) -> RegistrationProfile:
    first = faker.first_name()
    last = faker.last_name()
    return RegistrationProfile(
        password=password,
        name_sei=last,
        name_mei=first,
        kana_sei=last,
        kana_mei=first,
        phone_a=secrets.choice(["070", "080", "090"]),
        phone_e=four_digits(),
        phone_n=four_digits(),
    )
```

MVP 保留旧版行为：假名字段填入英文名。后续如目标站点要求片假名，可增加日文假名生成策略。

## 11. Matuya Client 详细设计

### 11.1 异常类型

`app/matuya/exceptions.py`

```python
class MatuyaError(Exception): ...
class MatuyaRequestError(MatuyaError): ...
class MatuyaFormParseError(MatuyaError): ...
class MatuyaSubmitError(MatuyaError): ...
```

### 11.2 HTML Parser

`app/matuya/parser.py`

```python
def extract_hidden_fields(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form")
    if form is None:
        raise MatuyaFormParseError("form not found")

    payload = {}
    for inp in form.find_all("input", {"type": "hidden"}):
        name = inp.get("name")
        value = inp.get("value")
        if name and value is not None:
            payload[name] = value

    if not payload:
        raise MatuyaFormParseError("hidden fields not found")

    return payload
```

旧版 `getHiddenItem` 不校验 `form` 是否存在，新版必须显式报错，便于定位页面结构变更。

### 11.3 Client 初始化

`app/matuya/client.py`

```python
class MatuyaClient:
    def __init__(
        self,
        register_url: str,
        form_url: str,
        timeout_seconds: int,
        session_factory: Callable[[], requests.Session] = requests.Session,
    ): ...
```

默认请求头：

```python
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept-Language": "en,zh-CN;q=0.9,zh-HK;q=0.8,zh;q=0.7,ja;q=0.6",
}
```

### 11.4 发送注册邮件

接口：

```python
def send_register_mail(self, email: str) -> None: ...
```

流程：

1. 创建新的 `requests.Session`。
2. `GET register_url`。
3. 校验 HTTP 状态码是 2xx。
4. 从 HTML 解析 hidden fields。
5. 补充：

```python
payload.update({
    "mail": email,
    "submit": "Send mail",
})
```

6. `POST form_url`。
7. 校验 HTTP 状态码是 2xx 或 3xx 后最终响应 2xx。
8. 失败抛出 `MatuyaRequestError` 或 `MatuyaSubmitError`。

请求设置：

```python
session.get(..., headers=DEFAULT_HEADERS, allow_redirects=True, timeout=timeout)
session.post(..., data=payload, headers=DEFAULT_HEADERS, allow_redirects=True, timeout=timeout)
```

### 11.5 完成注册

接口：

```python
def complete_registration(self, register_url: str, profile: RegistrationProfile) -> None: ...
```

流程：

1. 创建新的 `requests.Session`。
2. `GET register_url`，打开邮件中的注册链接。
3. 解析 hidden fields。
4. 构造确认表单 payload：

```python
payload.update({
    "password": profile.password,
    "password:cf": profile.password,
    "name_mei": profile.name_mei,
    "kana_mei": profile.kana_mei,
    "name_sei": profile.name_sei,
    "kana_sei": profile.kana_sei,
    "phone:a": profile.phone_a,
    "phone:e": profile.phone_e,
    "phone:n": profile.phone_n,
    "mail_flag": "0",
    "submit": "Confirm",
})
```

5. `POST form_url` 提交确认页。
6. 解析确认页 hidden fields。
7. 构造最终 payload：

```python
payload2.update({
    "submit": "Register",
})
```

8. `POST form_url` 完成注册。
9. 校验响应状态码。

MVP 不强依赖页面文字判断成功，因为旧版也只要 POST 成功即返回 true。建议在日志中记录最终响应 URL 和状态码；后续可通过成功页关键字增强判断。

## 12. Mail Client 详细设计

### 12.1 异常类型

`app/mail/exceptions.py`

```python
class MailError(Exception): ...
class MailLoginError(MailError): ...
class MailSearchError(MailError): ...
class MailFetchError(MailError): ...
class MailParseError(MailError): ...
class MailTimeoutError(MailError): ...
```

### 12.2 邮件正文解析

`app/mail/parser.py`

```python
def extract_bodies(msg: email.message.Message) -> tuple[str, str]: ...
def extract_first_url(text: str) -> str | None: ...
def extract_register_link(text: str, html: str) -> str: ...
```

正文提取规则：

- 遍历 multipart。
- 跳过附件。
- 收集 `text/plain` 和 `text/html`。
- charset 缺失时使用 UTF-8。
- charset 不合法时 fallback 到 UTF-8。

URL 解析规则：

```python
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
```

优先级：

1. 先从 `text/plain` 提取 URL。
2. 再从 `text/html` 提取 URL。
3. HTML 提取前可用 BeautifulSoup 获取文本，也可以直接正则匹配 href。

解析失败抛出：

```python
MailParseError("register link not found")
```

### 12.3 IMAP Client

`app/mail/imap_client.py`

```python
class MailClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        max_wait_seconds: int,
        poll_interval_seconds: int,
        max_results: int = 20,
    ): ...

    def wait_register_link(self, recipient: str) -> str: ...
```

内部方法：

```python
def _connect(self) -> imaplib.IMAP4_SSL: ...
def _search_uids(self, conn: imaplib.IMAP4_SSL, recipient: str) -> list[bytes]: ...
def _fetch_body(self, conn: imaplib.IMAP4_SSL, uid: bytes) -> tuple[str, str]: ...
```

连接流程：

1. 创建 SSL context。
2. 登录 Gmail。
3. 选择 INBOX readonly。

```python
ctx = ssl.create_default_context()
conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
conn.login(username, password)
conn.select("INBOX", readonly=True)
```

查询规则：

```python
conn.uid("search", None, "OR", "TO", recipient, "CC", recipient)
```

处理顺序：

- 取最新 `max_results` 封。
- 从最新到最旧遍历，即 `reversed(uids[-max_results:])`。
- 只要解析到 URL 立即返回。
- 每轮查询失败时记录日志，但没有到最大等待时间前继续下一轮。

轮询规则：

```python
deadline = time.monotonic() + max_wait_seconds
while time.monotonic() < deadline:
    ...
    time.sleep(poll_interval_seconds)
    conn.noop()
raise MailTimeoutError(...)
```

旧版没有最大等待时间，新版必须超时退出，避免后台线程永久占用。

## 13. 注册编排详细设计

### 13.1 AccountService

`app/accounts/service.py`

```python
class AccountService:
    def __init__(
        self,
        account_repo_factory: Callable[[], AccountRepository],
        generator: AccountGenerator,
        matuya_client_factory: Callable[[], MatuyaClient],
        mail_client_factory: Callable[[], MailClient],
        task_runner: TaskRunner,
        max_email_generate_attempts: int = 10,
    ): ...

    def enqueue_single_register(self, created_by: int) -> Account: ...
    def enqueue_batch_register(self, count: int, created_by: int) -> list[Account]: ...
    def run_registration(self, account_id: int) -> RegistrationResult: ...
    def list_accounts(self, status: str | None, page: int, page_size: int) -> Page: ...
    def get_account(self, account_id: int) -> Account | None: ...
    def record_copy(self, account_id: int) -> CopyResult: ...
```

### 13.2 创建唯一账号

```python
def _create_pending_unique_account(created_by: int) -> Account:
    last_error = None
    for _ in range(max_email_generate_attempts):
        email = generator.generate_email()
        password = generator.generate_password()
        try:
            return repo.create_pending(email, password, created_by)
        except DuplicateEmailError as exc:
            last_error = exc
            continue
    raise EmailGenerateExhaustedError(...) from last_error
```

设计原因：

- 生成器不查库，保持纯逻辑。
- 数据库唯一索引是并发唯一性的最终保证。
- 每次冲突重新生成 email 和 password，避免状态不一致。

### 13.3 发起单个注册

```python
def enqueue_single_register(created_by: int) -> Account:
    account = _create_pending_unique_account(created_by)
    task_runner.submit(self.run_registration, account.id)
    return account
```

返回时状态通常是 `pending`。线程池调度后会很快变为 `running`。

### 13.4 发起批量注册

```python
def enqueue_batch_register(count: int, created_by: int) -> list[Account]:
    if count < 1 or count > config.batch_max_count:
        raise ValidationError(...)

    accounts = []
    for _ in range(count):
        account = _create_pending_unique_account(created_by)
        accounts.append(account)

    for account in accounts:
        task_runner.submit(self.run_registration, account.id)

    return accounts
```

创建记录和提交任务分两段：

- 避免前几个任务先运行、后续创建失败时接口返回混乱。
- 保证接口返回的 `account_ids` 都已经落库。

### 13.5 单条注册任务

状态阶段：

| 阶段 | 说明 |
| --- | --- |
| `mark_running` | 将记录置为 running |
| `send_register_mail` | 提交邮箱，触发目标站点发邮件 |
| `wait_register_link` | 从 Gmail IMAP 等待注册链接 |
| `generate_profile` | 生成姓名、电话等表单字段 |
| `complete_registration` | 打开注册链接，两段提交完成注册 |
| `mark_success` | 将记录置为 success |
| `mark_failed` | 任一步失败时落库失败 |

伪代码：

```python
def run_registration(account_id: int) -> RegistrationResult:
    account = repo.get(account_id)
    if account is None:
        return RegistrationResult(account_id, AccountStatus.FAILED, "记录不存在")

    try:
        account = repo.mark_running(account_id)
        logger.info("registration stage", extra={...})

        matuya = matuya_client_factory()
        mail = mail_client_factory()

        matuya.send_register_mail(account.email)
        register_url = mail.wait_register_link(account.email)
        profile = generator.generate_profile(account.password)
        matuya.complete_registration(register_url, profile)

        repo.mark_success(account_id)
        return RegistrationResult(account_id, AccountStatus.SUCCESS)
    except Exception as exc:
        message = normalize_registration_error(exc)
        repo.mark_failed(account_id, message)
        logger.exception("registration failed", extra={...})
        return RegistrationResult(account_id, AccountStatus.FAILED, message)
```

### 13.6 错误归一化

```python
def normalize_registration_error(exc: Exception) -> str:
    if isinstance(exc, ConfigError):
        return "error.registration.config_missing"
    if isinstance(exc, MailLoginError):
        return "error.registration.mail_login_failed"
    if isinstance(exc, MailTimeoutError):
        return "error.registration.mail_timeout"
    if isinstance(exc, MailParseError):
        return "error.registration.mail_parse_failed"
    if isinstance(exc, MatuyaRequestError):
        return "error.registration.matuya_request_failed"
    if isinstance(exc, MatuyaFormParseError):
        return "error.registration.matuya_form_changed"
    if isinstance(exc, MatuyaSubmitError):
        return "error.registration.matuya_submit_failed"
    if isinstance(exc, EmailGenerateExhaustedError):
        return "error.registration.email_conflict_exhausted"
    return "error.registration.unknown"
```

数据库 `error_message` 保存错误 key，不保存固定语言文案。页面和 API 根据当前 locale 翻译展示；容器日志记录原始异常。

## 14. 任务执行器详细设计

`app/accounts/tasks.py`

```python
class TaskRunner:
    def __init__(self, max_workers: int): ...
    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future: ...
    def shutdown(self) -> None: ...
```

实现：

```python
self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="register")
```

异常处理：

- `run_registration` 内部必须捕获并落库异常。
- `TaskRunner.submit` 可包装 callback，记录未捕获异常。

```python
future.add_done_callback(_log_unhandled_exception)
```

容器关闭：

- Flask teardown 不关闭线程池。
- gunicorn worker 退出时通过 `atexit.register(task_runner.shutdown)` 释放资源。

MVP 限制：

- 任务状态只保存在 `matuya_accounts.status`。
- 容器重启后 `running` 记录不会恢复。
- 启动时可选择将上次遗留的 `running` 标记为 `failed`，错误 key 为 `error.registration.interrupted`。此行为建议实现，避免页面永久显示 running。

启动修复 SQL：

```sql
update matuya_accounts
set status = 'failed',
    error_message = 'error.registration.interrupted',
    completed_at = ?,
    updated_at = ?
where status = 'running';
```

## 15. 路由和 API 详细设计

### 15.1 Blueprint

| Blueprint | URL 前缀 | 文件 |
| --- | --- | --- |
| `auth` | 无 | `app/auth/routes.py` |
| `accounts` | 无 | `app/accounts/routes.py` |
| `i18n` | 无 | `app/i18n.py` 或 `app/auth/routes.py` |

### 15.2 页面路由

#### GET `/login`

行为：

- 已登录则跳转 `/`。
- 未登录渲染 `login.html`。

模板变量：

| 变量 | 说明 |
| --- | --- |
| `csrf_token` | CSRF token |
| `error` | 登录错误文案 |
| `next` | 登录成功后跳转地址 |

#### POST `/login`

Content-Type：`application/x-www-form-urlencoded`

入参：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `username` | 是 | 管理员用户名 |
| `password` | 是 | 管理员密码 |
| `_csrf_token` | 是 | CSRF token |
| `next` | 否 | 登录后跳转 |

成功：

- `302` 跳转 `next` 或 `/`。

失败：

- `200` 重新渲染登录页。
- 错误文案使用 `auth.invalid_credentials`。

#### POST `/logout`

行为：

- 校验 CSRF。
- 清空 Session。
- 跳转 `/login`。

#### POST `/locale`

行为：

- 校验 CSRF。
- 入参 `locale` 必须是 `en` 或 `zh-CN`。
- 写入 `session["locale"]`。
- HTML 表单提交时跳转回 `next` 或当前来源页。
- JSON 请求返回 `{ "locale": "..." }`。

#### GET `/`

行为：

- 需要登录。
- 查询第一页账号列表。
- 渲染 `accounts.html`。

查询参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `status` | 空 | 状态筛选 |
| `page` | `1` | 页码 |

### 15.3 API

所有 API：

- 需要登录。
- POST 需要 `X-CSRF-Token`。
- 返回 `application/json`。
- 错误响应同时包含稳定 `error` 和当前语言下的 `message`。

#### POST `/api/register`

功能：发起单个注册。

请求：无 body。

响应 `202`：

```json
{
  "account": {
    "id": 1,
    "email": "alice19940609a3f91c@example.com",
    "password": "A1b2C3d4E5f6G7",
    "status": "pending",
    "error_message": null,
    "copy_count": 0,
    "last_copied_at": null,
    "created_at": "2026-06-09T03:10:45Z",
    "updated_at": "2026-06-09T03:10:45Z"
  }
}
```

失败：

- `400` 参数或配置错误。
- `500` 未预期错误。

错误响应示例：

```json
{
  "error": "validation_failed",
  "message": "Please check your input."
}
```

#### POST `/api/register-batch`

请求：

```json
{
  "count": 3
}
```

响应 `202`：

```json
{
  "accounts": [
    { "id": 1, "email": "...", "password": "...", "status": "pending" },
    { "id": 2, "email": "...", "password": "...", "status": "pending" },
    { "id": 3, "email": "...", "password": "...", "status": "pending" }
  ]
}
```

校验：

- `count` 必须是整数。
- `count` 必须在 `1..BATCH_MAX_COUNT`。

#### GET `/api/accounts`

查询参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `status` | 空 | `pending`、`running`、`success`、`failed` |
| `page` | `1` | 页码 |
| `page_size` | `PAGE_SIZE_DEFAULT` | 每页数量 |

响应 `200`：

```json
{
  "items": [
    {
      "id": 1,
      "email": "alice19940609a3f91c@example.com",
      "password": "A1b2C3d4E5f6G7",
      "status": "success",
      "error_message": null,
      "error_key": null,
      "copy_count": 2,
      "last_copied_at": "2026-06-09T03:16:00Z",
      "created_at": "2026-06-09T03:10:45Z",
      "updated_at": "2026-06-09T03:15:50Z",
      "started_at": "2026-06-09T03:10:46Z",
      "completed_at": "2026-06-09T03:15:50Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

#### GET `/api/accounts/<id>`

响应 `200`：

```json
{
  "account": {
    "id": 1,
    "email": "...",
    "password": "...",
    "status": "running",
    "error_message": null,
    "error_key": null
  }
}
```

不存在：

```json
{
  "error": "not_found",
  "message": "Record not found."
}
```

HTTP 状态码：`404`。

#### POST `/api/accounts/<id>/copy-account`

功能：记录一次邮箱账号复制行为。

响应 `200`：

```json
{
  "account_id": 1,
  "copy_count": 3,
  "last_copied_at": "2026-06-09T03:20:00Z"
}
```

说明：

- API 只记录复制次数，不返回密码。
- 前端应在浏览器本地完成复制后再调用该 API。
- 如果剪贴板 API 失败，不调用该 API。

## 16. 页面交互详细设计

### 16.1 `base.html`

基础模板包含：

- `<meta name="robots" content="noindex,nofollow">`
- viewport。
- CSS 引用。
- 当前登录用户。
- 退出登录表单。
- 语言切换控件。
- `window.APP_CONFIG = { csrfToken: "...", locale: "en", messages: {...} }`。

语言控件：

- 显示 `English` 和 `简体中文`。
- 当前语言使用 `aria-current="true"` 或选中状态。
- 切换时提交 `/locale`，成功后刷新当前页面。

### 16.2 `login.html`

元素：

- 用户名输入框。
- 密码输入框。
- 登录按钮。
- 错误提示区域。

交互：

- 普通表单提交，不需要 JavaScript。
- 登录失败保留用户名，不保留密码。
- 所有 label、按钮和错误提示使用 `t("...")`。

### 16.3 `accounts.html`

布局：

- 顶部栏：应用名、当前用户、退出。
- 操作区：单个注册按钮、批量数量输入、批量注册按钮。
- 筛选区：全部、注册中、成功、失败。
- 历史表格：邮箱、密码、状态、失败原因、复制次数、最近复制时间、创建时间、更新时间、操作。
- 分页区：上一页、下一页、总数。

状态样式：

| 状态 | 英语显示 | 简中显示 |
| --- | --- |
| `pending` | Pending | 等待中 |
| `running` | Running | 注册中 |
| `success` | Success | 成功 |
| `failed` | Failed | 失败 |

按钮状态：

- 发起注册期间禁用提交按钮。
- 批量数量超出范围时禁用批量按钮或显示错误。
- `running` 和 `pending` 记录显示状态刷新。
- 表格标题、按钮、状态、空列表文案都使用 i18n key。

### 16.4 `static/app.js`

职责：

- 发起单个注册。
- 发起批量注册。
- 轮询新创建账号状态。
- 复制邮箱和密码。
- 复制邮箱成功后调用 copy API。
- 定时刷新列表中 `pending`、`running` 记录。
- 读取 `window.APP_CONFIG.messages` 生成动态文案。

轮询策略：

- 新建记录后立即插入表格顶部。
- 对 `pending`、`running` 的记录每 3 秒调用 `GET /api/accounts/<id>`。
- 记录变为 `success` 或 `failed` 后停止轮询。
- 全局最多同时轮询 20 条，避免页面后台占用过多请求。

复制策略：

```javascript
await navigator.clipboard.writeText(email)
await fetch(`/api/accounts/${id}/copy-account`, { method: "POST", headers })
```

密码复制：

- MVP 不统计密码复制。
- 只调用 `navigator.clipboard.writeText(password)`。

兼容策略：

- 如果 `navigator.clipboard` 不可用，使用隐藏 textarea 和 `document.execCommand("copy")` fallback。

前端翻译辅助：

```javascript
function t(key, fallback = key) {
  return window.APP_CONFIG?.messages?.[key] || fallback;
}
```

## 17. 序列化设计

`app/accounts/routes.py` 中提供：

```python
def serialize_account(account: Account, translate: Callable[[str], str]) -> dict[str, Any]:
    return {
        "id": account.id,
        "email": account.email,
        "password": account.password,
        "status": account.status.value,
        "error_key": account.error_message,
        "error_message": translate(account.error_message) if account.error_message else None,
        "copy_count": account.copy_count,
        "last_copied_at": account.last_copied_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
        "started_at": account.started_at,
        "completed_at": account.completed_at,
    }
```

安全说明：

- API 返回 password 是需求要求的后台历史展示能力。
- 所有账号 API 必须登录。
- 后续如果增加多用户权限，需要按 `created_by` 限制可见范围。
- `error_key` 是数据库中保存的稳定错误 key，`error_message` 是当前语言下的展示文案。

## 18. 日志详细设计

`app/logging.py`

### 18.1 日志格式

MVP 使用标准 logging，输出到 stdout。

推荐格式：

```text
%(asctime)s %(levelname)s %(name)s account_id=%(account_id)s email=%(email)s stage=%(stage)s message=%(message)s
```

为了避免普通日志缺少 extra 字段导致格式化失败，可使用 `LoggerAdapter` 或自定义 Formatter 补默认字段。

### 18.2 注册阶段日志

每个阶段记录：

| 字段 | 说明 |
| --- | --- |
| `account_id` | 注册记录 ID |
| `email` | 目标邮箱 |
| `stage` | 当前阶段 |
| `status` | `start`、`success`、`failed` |
| `duration_ms` | 阶段耗时 |

示例：

```python
logger.info(
    "send register mail completed",
    extra={
        "account_id": account.id,
        "email": account.email,
        "stage": "send_register_mail",
        "status": "success",
        "duration_ms": duration_ms,
    },
)
```

异常时使用 `logger.exception`，但页面只展示归一化文案。

## 19. 安全详细设计

### 19.1 登录保护

- `/login` 和静态资源可匿名访问。
- `/`、`/api/*`、`/logout` 必须登录。
- 未登录 API 返回 `401`，页面请求跳转 `/login`。

### 19.2 Session Cookie

Flask 配置：

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
```

如果部署在 HTTPS 后面，设置 `SESSION_COOKIE_SECURE=true`。

### 19.3 敏感信息

- Gmail app password 不写入代码库。
- `.env` 加入 `.gitignore`。
- 页面错误不显示原始异常堆栈。
- 日志不打印 Gmail 密码、管理员密码、Session、CSRF token。
- Matuya 明文密码属于业务需求，保存数据库并通过后台展示；应通过登录、文件权限和部署隔离保护。

### 19.4 限流和并发

MVP 通过以下方式降低滥用风险：

- `BATCH_MAX_COUNT` 限制单次批量数量。
- `BATCH_MAX_WORKERS` 限制真实并发。
- 按钮提交中禁用，防止重复点击。
- 后端不信任前端，仍做数量校验。

后续可加入基于 Session 或 IP 的简单频率限制。

## 20. Docker 详细设计

### 20.1 `requirements.txt`

建议依赖：

```text
Flask>=3.0,<4
gunicorn>=22,<24
requests>=2.31,<3
beautifulsoup4>=4.12,<5
Faker>=25,<40
Werkzeug>=3.0,<4
pytest>=8,<9
```

如测试依赖不希望进入生产镜像，可拆分 `requirements-dev.txt`。

### 20.2 `Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8926

CMD ["gunicorn", "-b", "0.0.0.0:8926", "wsgi:app"]
```

### 20.3 `docker-compose.yml`

```yaml
services:
  app:
    build: .
    ports:
      - "8926:8926"
    env_file:
      - .env
    volumes:
      - matuya_data:/data
    restart: unless-stopped

volumes:
  matuya_data:
```

### 20.4 `.dockerignore`

```text
.git
.venv
__pycache__
.pytest_cache
.env
*.pyc
```

## 21. 应用启动流程

`wsgi.py`：

```python
from app import create_app

app = create_app()
```

`app/__init__.py`：

```python
def create_app() -> Flask:
    app = Flask(__name__)

    config = load_config()
    app.secret_key = config.secret_key
    app.config["APP_CONFIG"] = config

    configure_logging()
    init_db_app(app)

    with app.app_context():
        run_migrations(get_db())
        ensure_initial_admin()
        mark_interrupted_running_accounts()

    register_security_hooks(app)
    register_blueprints(app)
    register_template_helpers(app)
    register_task_shutdown(app)

    return app
```

注意：

- `ensure_initial_admin` 只依赖数据库和环境变量。
- `MatuyaClient`、`MailClient` 不在启动时访问外部网络。
- `TaskRunner` 在 app 创建时初始化，但只在 API 请求后提交任务。

## 22. 测试详细设计

### 22.1 测试配置

`tests/conftest.py`：

- 使用临时 SQLite 文件。
- 设置测试环境变量。
- 创建 Flask test client。
- 禁用真实外部调用。
- CSRF 可在部分路由测试中关闭，另设测试覆盖 CSRF 失败。

### 22.2 Generator 测试

用例：

- `generate_email` 以配置的 `MAIL_SUFFIX` 结尾。
- 邮箱本地部分只包含字母数字。
- 多次生成有随机片段。
- `generate_password` 长度正确。
- 密码至少包含大小写字母和数字。
- `generate_profile` 字段完整，电话分段格式正确。

### 22.3 Repository 测试

用例：

- 创建 pending 记录成功。
- 重复 email 触发唯一冲突。
- `mark_running` 设置 started_at。
- `mark_success` 设置 completed_at。
- `mark_failed` 保存失败原因。
- `list` 支持状态筛选和分页。
- `increment_copy_count` 连续调用后计数正确。

### 22.4 Auth 测试

用例：

- 首次启动创建管理员。
- 管理员密码保存为 hash，不等于明文。
- 正确密码登录成功。
- 错误密码登录失败。
- 未登录访问 `/` 跳转 `/login`。
- 未登录访问 `/api/accounts` 返回 `401`。
- 登出后不能访问后台。

### 22.5 i18n 测试

用例：

- 无 `Accept-Language` 时默认 `en`。
- `Accept-Language: zh-CN,zh;q=0.9` 时选择 `zh-CN`。
- `Accept-Language: ja,en;q=0.8` 时选择 `en`。
- `POST /locale` 可写入 Session 并影响后续页面。
- `en.json` 和 `zh-CN.json` key 集合一致。
- API 错误响应包含 `error` 和本地化 `message`。

### 22.6 Parser 测试

Matuya parser：

- 从 fixture HTML 提取 hidden fields。
- 无 form 抛出 `MatuyaFormParseError`。
- form 无 hidden 抛出 `MatuyaFormParseError`。

Mail parser：

- 从纯文本邮件提取 URL。
- 从 HTML 邮件 href 提取 URL。
- 无 URL 抛出 `MailParseError`。
- multipart 附件被跳过。

### 22.7 Service 测试

使用 fake client：

```python
class FakeMatuyaClient:
    def send_register_mail(self, email): ...
    def complete_registration(self, register_url, profile): ...

class FakeMailClient:
    def wait_register_link(self, recipient): return "https://example.invalid/register-token"
```

用例：

- 成功注册：状态从 pending 到 running 到 success。
- Matuya 失败：状态 failed，错误文案归一化。
- Mail 超时：状态 failed，错误文案归一化。
- 邮箱冲突：重试后成功创建。
- 邮箱冲突重试耗尽：接口返回错误。

### 22.8 Route 测试

用例：

- `POST /api/register` 返回 `202` 和账号。
- `POST /api/register-batch` 校验 count。
- `GET /api/accounts` 返回分页结构。
- `GET /api/accounts/<id>` 不存在返回 `404`。
- `POST /api/accounts/<id>/copy-account` 递增复制次数。
- POST 缺少 CSRF 返回 `400`。
- `POST /locale` 拒绝不支持的语言。

## 23. MVP 编码顺序

1. 建立目录结构、`wsgi.py`、配置模块和基础依赖。
2. 实现数据库连接、迁移机制和初始 SQL。
3. 实现 i18n 资源加载、语言识别、模板 helper 和 `/locale`。
4. 实现 `UserRepository`、`AuthService`、登录页和登录保护。
5. 实现 `AccountRepository`、`AccountGenerator` 和序列化。
6. 实现 Matuya parser/client，并用 fixture 测试。
7. 实现 mail parser/client，并用 fixture 测试。
8. 实现 `TaskRunner` 和 `AccountService.run_registration`。
9. 实现账号 API：单个注册、批量注册、列表、详情、复制统计。
10. 实现 `accounts.html`、`app.css`、`app.js`。
11. 补齐 Dockerfile、Compose、`.env.example`。
12. 跑通离线测试。
13. 在配置真实测试环境后人工验证完整注册链路。

## 24. 验收用例映射

| 验收项 | 详细设计覆盖 |
| --- | --- |
| Docker Compose 可启动 | 第 20 章 |
| 首次启动创建管理员 | 第 8、21 章 |
| 未登录跳转登录页 | 第 8、15、19 章 |
| 按浏览器语言自动切换，默认英语 | 第 9、16 章 |
| 登录后发起单个注册 | 第 13、15、16 章 |
| 批量注册受数量和并发限制 | 第 13、14、15、19 章 |
| 邮箱不重复 | 第 7、10、13 章 |
| 随机密码保存并展示 | 第 6、7、10、15、17 章 |
| 历史列表筛选分页 | 第 7、15、16 章 |
| 复制账号次数持久化 | 第 7、15、16 章 |
| 配置不硬编码 | 第 4 章 |
| 注册失败原因落库并本地化展示 | 第 7、9、13、18 章 |
| 外部表单和邮件解析可测试 | 第 11、12、22 章 |

## 25. 主要风险和实现注意事项

| 风险 | 细节 | 实现注意事项 |
| --- | --- | --- |
| 目标页面结构变化 | hidden fields 或 form 不存在 | Parser 必须抛明确异常，Service 落库失败原因 |
| Gmail IMAP 搜索不稳定 | 可能搜索到旧邮件或延迟邮件 | 从最新到最旧遍历，轮询到超时，按收件人过滤 |
| 线程池任务丢失 | 容器重启导致 running 停滞 | 启动时将遗留 running 标记 failed |
| SQLite 写并发 | 多任务同时更新状态和复制次数 | WAL、busy timeout、短事务 |
| 明文 Matuya 密码 | 后台需要回显，存在泄露风险 | 登录保护、数据库权限、日志不输出密码 |
| 重复提交注册 | 用户重复点击或并发请求 | 前端禁用按钮，后端数量和线程池限制 |
| CSRF 影响 API 调用 | 前端忘记传 token | base 模板统一注入 token，fetch 包装统一加 header |
