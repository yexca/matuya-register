# Matuya 注册工具重写需求分析

## 1. 背景与目标

现有 `matuya-register` 已经验证了核心链路：

1. 生成一个随机邮箱地址。
2. 打开 Matuya 注册入口并提交邮箱。
3. 通过 Gmail IMAP 查询该邮箱收到的注册链接。
4. 打开注册链接，填入随机姓名、电话、密码等表单字段。
5. 提交确认页并完成注册。
6. 前端支持单个或批量注册，并展示账号与密码。

新程序只参考上述业务逻辑，重新设计为轻量化、可 Docker 部署、模块化、高内聚低耦合的应用。重点补齐旧版缺失的账号系统、注册记录持久化、随机密码、唯一账号控制和后台历史查询能力。

## 2. 设计原则

- 轻量化：优先选择少量依赖、低运维成本、单容器可运行的架构。
- 模块化：注册流程、邮件读取、账号生成、数据库访问、后台登录、页面展示彼此隔离。
- 高内聚低耦合：每个模块只处理自己的领域逻辑，通过清晰接口交互，避免在路由层堆业务代码。
- 可追踪：每一次注册请求、成功账号、失败原因都应保存，方便后台查看和排错。
- 可配置：注册入口、表单提交地址、Gmail IMAP 凭据、邮箱后缀、并发数、超时时间等通过环境变量配置。
- 安全默认值：后台必须登录；管理员密码只保存哈希；敏感配置不写入代码仓库。
- 合规使用：仅用于被授权的学习、测试或个人场景；应提供限流、并发上限和免责声明，避免违反目标网站条款。

## 3. 目标用户与使用场景

### 3.1 管理员

- 登录后台。
- 发起单个或批量 Matuya 账号注册。
- 查看自己生成过的 Matuya 账号、随机密码、注册状态、失败原因和创建时间。
- 复制账号密码。
- 查看每个 Matuya 账号被复制的累计次数。
- 根据状态筛选历史记录。

### 3.2 系统维护者

- 使用 Docker 或 Docker Compose 部署。
- 通过环境变量配置 Gmail、Matuya 注册地址、邮箱后缀、数据库路径等。
- 查看容器日志定位注册失败原因。
- 备份 SQLite 数据库文件。

## 4. 功能需求

### 4.1 后台账号系统

必须提供本系统自己的登录能力，和 Matuya 账号区分。

- 支持管理员登录、登出。
- 后台页面未登录不可访问。
- 管理员密码使用安全哈希保存，例如 Werkzeug password hash、bcrypt 或 Argon2。
- MVP 可只支持单管理员。
- 初始管理员建议通过环境变量创建：
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD`
- 后续增强可支持多用户、修改密码、禁用用户。

### 4.2 Matuya 账号生成

- 每次注册前生成新的邮箱地址。
- 邮箱生成必须避免重复。
- 推荐策略：
  - 不只依赖“生成后查询是否存在”。
  - 数据库表对 `email` 建唯一索引。
  - 生成邮箱后先写入一条 `pending` 记录。
  - 如果插入触发唯一约束冲突，则重新生成并重试。
  - 这样即使并发注册，也能由数据库保证唯一性。
- 邮箱生成可沿用旧版思路：随机英文名 + 日期/随机片段 + 邮箱后缀。
- 为降低碰撞概率，建议加入高熵随机片段，例如 `secrets.token_hex(3)` 或随机数字串。

### 4.3 随机密码

- Matuya 账号密码每次随机生成。
- 使用 `secrets` 生成，不使用 `random`。
- 默认长度建议 12-16 位。
- 默认字符集包含大小写字母、数字。
- 如目标站点允许，可加入安全符号；如表单兼容性不确定，MVP 可先不加入符号。
- 随机密码需要保存到数据库，因为后台需要展示历史 Matuya 账号和密码。
- 因密码需要可回显，不能只保存哈希；应通过后台鉴权、数据库文件权限和部署环境保护。
- 后续增强可支持密码字段加密存储，密钥由环境变量提供。

### 4.4 注册流程

注册流程拆成独立服务，不直接写在路由函数中。

单个注册流程：

1. 生成唯一邮箱和随机密码。
2. 创建注册记录，状态为 `pending`。
3. 调用 Matuya 注册入口，提交邮箱。
4. 通过 IMAP 轮询最新邮件，解析注册链接。
5. 打开注册链接，获取隐藏字段。
6. 生成姓名、假名、电话等表单字段。
7. 提交确认表单。
8. 提交最终注册表单。
9. 成功则更新状态为 `success`。
10. 任一步失败则更新状态为 `failed`，记录错误信息。

旧版需要参考的外部行为：

- 发送注册邮件：GET `register_url`，解析隐藏字段，POST 到 `form_url`。
- 完成注册：GET 邮件中的链接，解析隐藏字段，POST 确认表单，再 POST 最终注册表单。
- 邮件读取：Gmail IMAP，按收件人地址搜索最新邮件，解析正文中的 URL。

新实现需要补充：

- HTTP 请求超时。
- IMAP 轮询最大等待时间。
- 每次注册的日志上下文。
- 失败状态落库。
- 注册结果结构化返回。

### 4.5 批量注册

- 管理员可选择生成数量。
- 单次批量数量必须有限制，默认建议最多 5 或 10。
- 并发数必须有限制，默认建议 2-3，避免目标站点或邮件服务压力过大。
- 批量注册应返回每个账号的独立状态。
- 推荐以后台任务方式处理：
  - MVP 可使用进程内线程池。
  - 每个账号有独立记录，页面轮询状态。
  - 不推荐长时间阻塞 HTTP 请求直到全部完成。
- 如果坚持轻量化，第一版可先同步执行单个注册，批量注册用小并发线程池，但接口必须设置合理超时。

### 4.6 历史记录后台

- 登录后默认进入历史列表。
- 列表字段：
  - Matuya 邮箱账号
  - Matuya 密码
  - 注册状态
  - 失败原因
  - 创建时间
  - 更新时间
  - 创建者
  - 账号复制次数
  - 最近复制时间
- 支持复制账号和密码。
- 复制 Matuya 账号成功后，系统需要记录该账号被复制的次数。
- 复制次数必须保存到数据库，刷新页面或重启容器后仍然保留。
- 复制次数统计针对 Matuya 邮箱账号；密码复制是否单独统计可作为后续增强。
- 支持按状态筛选：全部、注册中、成功、失败。
- 支持分页，避免记录多时页面变慢。
- 推荐提供“重新尝试失败记录”的入口，但 MVP 可不做。

### 4.7 配置管理

所有可变配置通过环境变量读取，提供 `.env.example`，不提交真实密钥。

建议配置项：

- `APP_SECRET_KEY`：后台 Session 密钥。
- `ADMIN_USERNAME`：初始管理员用户名。
- `ADMIN_PASSWORD`：初始管理员密码。
- `DATABASE_URL` 或 `SQLITE_PATH`：SQLite 数据库位置。
- `MATUYA_REGISTER_URL`：注册入口地址。
- `MATUYA_FORM_URL`：注册表单提交地址。
- `MAIL_IMAP_HOST`：默认 `imap.gmail.com`。
- `MAIL_IMAP_PORT`：默认 `993`。
- `MAIL_USERNAME`：Gmail 账号。
- `MAIL_PASSWORD`：Gmail app password。
- `MAIL_SUFFIX`：生成邮箱的后缀。
- `REGISTER_MAX_WAIT_SECONDS`：等待邮件最大时间。
- `REGISTER_POLL_INTERVAL_SECONDS`：邮件轮询间隔。
- `BATCH_MAX_COUNT`：单次批量最大数量。
- `BATCH_MAX_WORKERS`：批量并发上限。

## 5. 非功能需求

### 5.1 轻量化

- 推荐 Python 3.12。
- Web 框架可继续使用 Flask，减少迁移成本。
- 数据库使用 SQLite。
- 页面可使用 Jinja2 + 少量原生 JavaScript，不引入大型前端框架。
- ORM 可选：
  - 更轻量：标准库 `sqlite3` + repository 层。
  - 更易维护：SQLAlchemy。
- 若项目规模保持小型，建议优先使用 `sqlite3` + 明确的数据访问层。

### 5.2 Docker 部署

必须提供：

- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `.env.example`
- 数据库持久化 volume

运行方式示例：

```bash
docker compose up -d
```

SQLite 文件建议挂载到容器内 `/data/app.db`。

### 5.3 数据一致性

- `matuya_accounts.email` 必须有唯一索引。
- 注册状态只允许有限状态值，例如 `pending`、`running`、`success`、`failed`。
- 失败时保留已生成的邮箱和密码，方便排查。
- 账号复制次数递增必须使用数据库原子更新，例如 `copy_count = copy_count + 1`，避免并发点击造成丢失更新。
- 并发生成账号时，必须依赖数据库唯一约束兜底。
- SQLite 建议开启 WAL 模式，提高读写并发体验。

### 5.4 安全

- 管理后台必须启用登录。
- Session 使用强随机 `APP_SECRET_KEY`。
- 管理员密码不明文保存。
- Gmail 密码、IMAP 凭据、邮箱后缀不写死在代码中。
- 后台页面加 `noindex,nofollow`。
- 所有 POST 操作建议增加 CSRF 保护。
- 注册请求需要限制频率和并发。
- 错误信息在页面上简洁展示，详细堆栈只写日志。

### 5.5 可观测性

- 每次注册应有结构化日志。
- 日志至少包含：
  - 注册记录 ID
  - 邮箱
  - 当前阶段
  - 成功/失败
  - 错误原因
- 页面显示用户可理解的失败原因。
- 容器日志可用于定位 IMAP 登录失败、未收到邮件、目标站点表单变更等问题。

## 6. 建议模块划分

```text
app/
  __init__.py              # 创建 Flask app、注册蓝图、中间件
  config.py                # 环境变量配置
  db.py                    # SQLite 连接、迁移、事务
  models.py                # 数据结构或 SQL 常量
  auth/
    routes.py              # 登录、登出
    service.py             # 管理员校验、密码哈希
  accounts/
    routes.py              # 历史列表、发起注册、查询状态
    service.py             # 注册编排
    repository.py          # matuya_accounts 数据访问
    generator.py           # 邮箱、密码、姓名、电话生成
  matuya/
    client.py              # Matuya HTTP 表单交互
    parser.py              # HTML 隐藏字段解析
  mail/
    imap_client.py         # IMAP 连接、搜索、读取
    parser.py              # 邮件正文 URL 提取
  templates/
    login.html
    accounts.html
  static/
    app.css
    app.js
```

模块依赖方向建议：

```text
routes -> service -> repository
routes -> service -> matuya client
routes -> service -> mail client
service -> generator
```

路由层只处理 HTTP 入参、权限和响应，不直接操作 IMAP、requests 或 SQLite。

## 7. 数据库设计

### 7.1 `users`

保存后台用户。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer primary key | 用户 ID |
| username | text unique not null | 登录用户名 |
| password_hash | text not null | 密码哈希 |
| created_at | text not null | 创建时间 |
| updated_at | text not null | 更新时间 |

### 7.2 `matuya_accounts`

保存注册历史。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer primary key | 记录 ID |
| email | text unique not null | Matuya 登录邮箱 |
| password | text not null | Matuya 明文密码，用于后台回显 |
| status | text not null | `pending`、`running`、`success`、`failed` |
| error_message | text | 失败原因 |
| copy_count | integer not null default 0 | Matuya 邮箱账号被复制次数 |
| last_copied_at | text | 最近复制账号的时间 |
| created_by | integer | 后台用户 ID |
| started_at | text | 开始注册时间 |
| completed_at | text | 完成时间 |
| created_at | text not null | 创建时间 |
| updated_at | text not null | 更新时间 |

建议索引：

```sql
create unique index idx_matuya_accounts_email on matuya_accounts(email);
create index idx_matuya_accounts_status on matuya_accounts(status);
create index idx_matuya_accounts_created_at on matuya_accounts(created_at);
```

### 7.3 可选表：`registration_events`

如果需要更细的排错记录，可增加事件表。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer primary key | 事件 ID |
| account_id | integer not null | Matuya 账号记录 ID |
| stage | text not null | 当前阶段 |
| message | text | 日志消息 |
| created_at | text not null | 创建时间 |

MVP 可先不建该表，只记录最终状态和容器日志。

## 8. 页面与接口需求

### 8.1 页面

- `GET /login`：登录页。
- `POST /login`：提交登录。
- `POST /logout`：退出登录。
- `GET /`：历史账号列表和注册入口。

### 8.2 API

- `POST /api/register`
  - 功能：发起单个注册。
  - 返回：注册记录 ID、当前状态。

- `POST /api/register-batch`
  - 功能：发起批量注册。
  - 入参：`count`。
  - 返回：批量创建的记录 ID 列表。

- `GET /api/accounts`
  - 功能：查询历史记录。
  - 查询参数：`status`、`page`、`page_size`。

- `GET /api/accounts/<id>`
  - 功能：查询单条记录状态。

- `POST /api/accounts/<id>/copy-account`
  - 功能：记录一次 Matuya 邮箱账号复制行为。
  - 行为：在数据库中原子递增 `copy_count`，并更新 `last_copied_at`。
  - 返回：最新 `copy_count` 和 `last_copied_at`。

MVP 如果采用同步注册，也可以在 `POST /api/register` 直接返回最终账号和密码；但建议保留记录 ID，方便未来改成异步。

## 9. 注册状态机

```text
pending -> running -> success
pending -> running -> failed
failed -> running -> success  # 可选：重试
failed -> running -> failed   # 可选：重试失败
```

状态含义：

- `pending`：记录已创建，但任务尚未开始。
- `running`：注册流程执行中。
- `success`：注册完成，账号可用。
- `failed`：注册失败，查看 `error_message`。

## 10. 错误处理需求

需要区分以下常见错误：

- 配置缺失：Gmail、邮箱后缀、Matuya URL 未配置。
- 邮件服务登录失败。
- 等待注册链接超时。
- 邮件中未解析到链接。
- Matuya 注册入口访问失败。
- 表单隐藏字段解析失败。
- 最终注册提交失败或页面结构变更。
- 数据库唯一约束冲突重试耗尽。

页面只展示简短错误，日志保留详细上下文。

## 11. MVP 范围

第一版建议实现：

- Flask + SQLite + Jinja2。
- Docker Compose 部署。
- 单管理员登录。
- 单个注册。
- 小批量注册，限制数量和并发。
- 随机密码。
- 邮箱唯一约束。
- 注册历史列表。
- 状态筛选和复制账号密码。
- 环境变量配置。

暂不做：

- 多管理员权限体系。
- 分布式任务队列。
- 密码加密存储。
- 注册事件明细表。
- 失败任务一键重试。

## 12. 后续增强

- 将批量注册改为真正异步任务队列，例如 RQ、Celery 或 SQLite-backed 简易队列。
- 增加 `registration_events`，在后台展示每个账号的阶段日志。
- 增加密码加密存储。
- 增加管理员修改密码。
- 增加导出 CSV。
- 增加自动数据库备份说明。
- 增加 Playwright 或 requests mock 测试，避免目标站点结构变化时无声失败。

## 13. 验收标准

- 使用 `docker compose up -d` 可以启动应用。
- 首次启动可根据环境变量创建管理员。
- 未登录访问后台会跳转登录页。
- 登录后可以发起单个注册。
- 注册成功后，历史列表展示 Matuya 账号、随机密码、状态和时间。
- 点击复制 Matuya 账号后，该记录的复制次数会递增并持久化保存。
- 多次注册不会出现重复邮箱。
- 批量注册受最大数量和并发限制约束。
- Gmail、Matuya 地址、邮箱后缀等配置均不硬编码。
- SQLite 数据库文件通过 Docker volume 持久化。
- 注册失败时记录 `failed` 状态和失败原因。
