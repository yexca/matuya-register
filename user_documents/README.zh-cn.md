# Matuya 注册工具

Matuya 注册工具是一个轻量级 Flask 后台应用，用于在授权范围内发起 Matuya 注册流程。它支持单个或小批量注册，通过 Gmail IMAP 读取注册链接，提交目标注册表单，并把每条生成账号的状态、密码、失败原因和邮箱复制次数保存到 SQLite。

本项目仅用于获得授权的测试和维护场景。请勿用于违反法律、网站条款、账号政策或目标服务方要求的用途。

英文 README：[README.md](README.md)

## 功能

- 管理员登录和退出。
- 默认英文界面，支持简体中文。
- 单个注册和小批量注册。
- 随机邮箱生成，并通过 SQLite 唯一约束保证不重复。
- 随机 14 位密码，包含小写字母、大写字母和数字。
- 注册历史、状态筛选和分页。
- 本地化失败原因。
- 复制邮箱和密码。
- 持久化邮箱复制次数。
- Docker Compose 部署，SQLite 数据持久化。

## 运行要求

- 部署推荐 Docker 和 Docker Compose。
- 本地开发推荐 Python 3.12。
- 已获授权的 Matuya 注册入口和表单提交地址。
- 已启用 IMAP 的 Gmail 账号和 Gmail app password。

## 配置

复制环境变量示例：

```bash
cp .env.example .env
```

启动前请编辑 `.env`。

必填配置：

| 变量 | 说明 |
| --- | --- |
| `APP_SECRET_KEY` | Flask Session 使用的长随机密钥 |
| `ADMIN_USERNAME` | 初始管理员用户名 |
| `ADMIN_PASSWORD` | 初始管理员密码 |
| `MATUYA_REGISTER_URL` | 授权使用的 Matuya 注册入口 |
| `MATUYA_FORM_URL` | 授权使用的 Matuya 表单提交地址 |
| `MAIL_USERNAME` | 用于读取注册邮件的 Gmail 地址 |
| `MAIL_PASSWORD` | Gmail app password |
| `MAIL_SUFFIX` | 生成邮箱使用的后缀，例如 `@example.com` |

常用可选配置：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SQLITE_PATH` | `/data/app.db` | SQLite 数据库路径 |
| `BATCH_MAX_COUNT` | `5` | 单次批量注册数量上限 |
| `BATCH_MAX_WORKERS` | `2` | 当前进程内注册任务并发数 |
| `REGISTER_MAX_WAIT_SECONDS` | `90` | 等待注册邮件的最长秒数 |
| `REGISTER_POLL_INTERVAL_SECONDS` | `5` | 邮件轮询间隔秒数 |
| `HTTP_TIMEOUT_SECONDS` | `20` | Matuya HTTP 请求超时秒数 |
| `SESSION_COOKIE_SECURE` | `false` | HTTPS 部署时设为 `true` |

不要提交 `.env`、真实 Gmail app password 或生产密钥。

## 使用 Docker Compose 运行

构建并启动：

```bash
docker compose build
docker compose up -d
```

打开：

```text
http://localhost:8926
```

查看日志：

```bash
docker compose logs -f app
```

停止：

```bash
docker compose down
```

## 使用后台页面

1. 使用 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 登录。
2. 点击“注册单个”发起单个注册任务。
3. 输入数量并点击“批量注册”发起小批量任务。
4. 使用状态筛选查看等待中、注册中、成功或失败记录。
5. 在历史表格中复制邮箱或密码。

页面会自动轮询正在执行的任务。复制邮箱会增加复制次数；复制密码不会增加复制次数。

## SQLite 数据

容器内数据库位置：

```text
/data/app.db
```

`docker-compose.yml` 会把 `/data` 挂载到命名 volume `matuya_data`，因此历史记录和复制次数会在容器重启后保留。

备份数据库：

```bash
docker compose exec app sh -c 'cp /data/app.db /data/app.db.backup'
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /data/app.db /backup/app.db
```

恢复前请先停止应用：

```bash
docker compose down
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /backup/app.db /data/app.db
docker compose up -d
```

## 本地开发

安装依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

运行测试：

```bash
python -m pytest -q
```

本地启动：

```bash
export $(grep -v '^#' .env | xargs)
flask --app wsgi run --host 127.0.0.1 --port 8926
```

## 运维说明

- 注册任务运行在当前进程内的 `ThreadPoolExecutor`。
- 应用重启会中断执行中的任务；启动时会把遗留的 `running` 记录标记为 `error.registration.interrupted`。
- Matuya 账号密码为了后台展示和复制而明文保存。请保护数据库文件、备份文件和部署主机。
- 自动化测试使用 fake client 和 fixture，不访问真实 Matuya 或 Gmail。真实链路需要在授权范围内人工验证。

