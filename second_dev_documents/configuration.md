# 配置说明

配置由 `app/config.py` 从环境变量读取。缺少必填配置或类型不合法时，应用启动失败并抛出 `ConfigError`。

## 环境变量

| 变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `APP_SECRET_KEY` | 无 | 是 | Flask Session 密钥，生产环境应使用长随机字符串 |
| `ADMIN_USERNAME` | 无 | 是 | 初始管理员用户名 |
| `ADMIN_PASSWORD` | 无 | 是 | 初始管理员密码；每次启动会更新该管理员的密码哈希 |
| `SQLITE_PATH` | `/data/app.db` | 否 | SQLite 数据库路径 |
| `MATUYA_REGISTER_URL` | 无 | 是 | 授权使用的 Matuya 注册入口 |
| `MATUYA_FORM_URL` | 无 | 是 | 授权使用的 Matuya 表单提交地址 |
| `MAIL_IMAP_HOST` | `imap.gmail.com` | 否 | IMAP Host |
| `MAIL_IMAP_PORT` | `993` | 否 | IMAP SSL 端口 |
| `MAIL_USERNAME` | 无 | 是 | Gmail 账号 |
| `MAIL_PASSWORD` | 无 | 是 | Gmail app password |
| `MAIL_SUFFIX` | 无 | 是 | 生成邮箱的后缀，必须以 `@` 开头 |
| `REGISTER_MAX_WAIT_SECONDS` | `90` | 否 | 等待注册邮件的最大秒数 |
| `REGISTER_POLL_INTERVAL_SECONDS` | `5` | 否 | 邮件轮询间隔秒数 |
| `HTTP_TIMEOUT_SECONDS` | `20` | 否 | Matuya HTTP 请求超时秒数 |
| `BATCH_MAX_COUNT` | `5` | 否 | 单次批量注册数量上限，范围 `1..50` |
| `BATCH_MAX_WORKERS` | `2` | 否 | 注册线程池并发上限，范围 `1..10` |
| `PAGE_SIZE_DEFAULT` | `20` | 否 | 历史列表默认分页大小 |
| `PAGE_SIZE_MAX` | `50` | 否 | API 允许的最大分页大小 |
| `ENABLE_CSRF` | `true` | 否 | 是否启用 CSRF 校验 |
| `DEFAULT_LOCALE` | `en` | 否 | 默认界面语言 |
| `SUPPORTED_LOCALES` | `en,zh-CN` | 否 | 支持的语言；当前只允许 `en` 和 `zh-CN` |
| `SESSION_COOKIE_SECURE` | `false` | 否 | HTTPS 部署时应设为 `true` |

## 校验规则

- 必填项不能为空。
- 整数项必须能转换为整数。
- `MAIL_IMAP_PORT`、`REGISTER_MAX_WAIT_SECONDS`、`REGISTER_POLL_INTERVAL_SECONDS`、`HTTP_TIMEOUT_SECONDS` 必须大于 0。
- `MAIL_SUFFIX` 必须以 `@` 开头。
- `BATCH_MAX_COUNT` 必须在 `1..50`。
- `BATCH_MAX_WORKERS` 必须在 `1..10`。
- `PAGE_SIZE_DEFAULT` 必须在 `1..PAGE_SIZE_MAX`。
- `SUPPORTED_LOCALES` 只能包含 `en` 和 `zh-CN`。
- `DEFAULT_LOCALE` 必须包含在 `SUPPORTED_LOCALES` 中。

## Matuya URL 核对

`MATUYA_REGISTER_URL` 必须是打开注册页面的完整入口地址，`MATUYA_FORM_URL` 必须是该页面表单实际提交的完整地址。两者通常来自同一个授权注册页面，但不一定完全相同；配置前应在浏览器或开发者工具中确认表单的 `action`。

如果注册任务失败并显示 `error.registration.matuya_request_failed`，先确认 URL 主机名可以解析。以下命令应至少返回一个 IP 地址：

```bash
python3 - <<'PY'
import socket
from urllib.parse import urlparse

for url in [
    "替换为 MATUYA_REGISTER_URL",
    "替换为 MATUYA_FORM_URL",
]:
    host = urlparse(url).hostname
    print(url)
    print(socket.getaddrinfo(host, 443)[0][4])
PY
```

Docker 部署时也应在容器内做同样检查：

```bash
docker compose exec app python - <<'PY'
import socket
for host in ["替换为 Matuya URL 的主机名", "imap.gmail.com"]:
    try:
        print(host, socket.getaddrinfo(host, 443)[0][4])
    except Exception as exc:
        print(host, type(exc).__name__, exc)
PY
```

如果 `imap.gmail.com` 可以解析但 Matuya 主机名不能解析，通常是 Matuya URL 填写错误、授权入口已过期、目标服务 DNS 暂不可用，或当前网络无法访问该域名。部分授权入口可能限制日本出口 IP，非日本网络可能表现为 DNS 失败、连接超时或拒绝访问；此时应切换到允许的日本出口网络后重试，而不是调整 Gmail 配置。

## `.env` 示例

从应用目录复制：

```bash
cd matuya-register
cp .env.example .env
```

最小生产配置应至少替换这些值：

```env
APP_SECRET_KEY=replace-with-a-long-random-string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
MATUYA_REGISTER_URL=https://authorized.example/register
MATUYA_FORM_URL=https://authorized.example/form
MAIL_USERNAME=your-gmail@example.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_SUFFIX=@example.com
SESSION_COOKIE_SECURE=true
```

## 安全注意事项

- `.env` 不应提交到仓库。
- `MAIL_PASSWORD` 应使用 Gmail app password，不要使用主账号密码。
- Matuya 账号密码以明文保存在 SQLite，因为后台需要显示和复制。必须保护 `/data/app.db`、备份文件和宿主机访问权限。
- 对外网部署时建议放在 HTTPS 反向代理后，并设置 `SESSION_COOKIE_SECURE=true`。
- 管理员密码哈希由 Werkzeug `pbkdf2:sha256` 生成。
- 所有 POST 请求默认需要 CSRF token。

## 数据库与持久化

Docker Compose 将容器内 `/data` 挂载到命名 volume `matuya_data`，默认数据库路径为：

```text
/data/app.db
```

本地开发可以设置：

```env
SQLITE_PATH=./data/app.db
```

SQLite 连接策略：

- 每个请求使用独立连接。
- 启用 `foreign_keys`。
- 设置 `busy_timeout = 30000`。
- 初始化时启用 WAL。
- 时间统一保存为 UTC ISO8601 字符串。
