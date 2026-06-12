# 测试与部署

## 自动测试

测试目录：

```text
matuya-register/tests/
```

运行：

```bash
cd matuya-register
python -m pytest -q
```

当前测试为离线测试，不访问真实 Gmail 或 Matuya。外部行为通过 fake client 和 fixture 验证。

主要覆盖：

- 配置和应用初始化。
- 初始管理员创建、登录、登出、未登录拦截。
- CSRF 拦截。
- i18n 默认语言、浏览器语言识别、语言切换、locale key 一致性。
- 账号 repository 创建、唯一冲突、状态更新、分页、复制计数。
- 邮箱、密码、注册资料生成。
- Matuya HTML hidden fields 解析。
- 邮件正文和 HTML 链接解析。
- 注册 service 成功路径和典型失败路径。
- API 注册、批量校验、账号查询和复制计数。

## 增加测试的建议

| 变更类型 | 建议测试 |
| --- | --- |
| 新配置项 | 配置默认值、类型转换、非法值启动失败 |
| 新数据库字段 | migration、repository 写入读取、序列化 |
| 新 API | 未登录、CSRF、成功响应、参数错误 |
| 新注册阶段 | service 成功路径、异常归一化、日志字段 |
| 新外部 client | parser fixture、请求异常映射、超时路径 |
| 新文案 | `test_locale_catalog_keys_match` |

## Docker 部署

应用目录内已提供：

```text
Dockerfile
docker-compose.yml
.env.example
.dockerignore
```

启动：

```bash
cd matuya-register
cp .env.example .env
# 编辑 .env，替换真实授权配置
docker compose build
docker compose up -d
```

访问：

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

## 数据备份与恢复

默认数据库位于容器内：

```text
/data/app.db
```

Compose 使用命名 volume：

```text
matuya_data
```

备份：

```bash
cd matuya-register
docker compose exec app sh -c 'cp /data/app.db /data/app.db.backup'
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /data/app.db /backup/app.db
```

恢复前应停止应用：

```bash
docker compose down
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /backup/app.db /data/app.db
docker compose up -d
```

## 人工验收清单

在具备授权测试配置后，建议按以下顺序验收：

- Docker Compose 可以启动。
- `/login` 返回登录页。
- 未登录访问 `/` 跳转登录页。
- 未登录访问 `/api/accounts` 返回 `401`。
- 管理员可以登录和登出。
- 默认英文界面可用。
- 浏览器 `Accept-Language: zh-CN` 或页面语言切换可显示简体中文。
- 单个注册会新增记录并进入 `pending` 或 `running`。
- 注册成功后状态变为 `success`，显示邮箱和随机密码。
- 注册失败后状态变为 `failed`，显示本地化失败原因。
- 批量数量超过 `BATCH_MAX_COUNT` 会被拒绝。
- 宽屏下账号列表应尽量完整显示邮箱和密码；窄屏下由 CSS 单行省略，不应在模板或 JS 中写死短文本。
- 手机端邮箱、密码和复制次数应尽量同一行展示；状态和详情可换到下一行。
- 点击邮箱文本或旁边的 `copy` 按钮都会复制完整邮箱，自动复制成功后增加 `copy_count`。
- 点击密码文本或旁边的 `copy` 按钮会复制完整密码，但不会增加 `copy_count`。
- 若浏览器拒绝自动写入剪贴板，应显示手动复制弹层并选中文本；该 fallback 不应增加邮箱复制次数。
- 详情弹层在手机端可打开、内容区可滚动，关闭按钮位于弹层底部。
- 刷新页面后历史记录和复制次数仍存在。
- 重启容器后数据仍存在。
- 重启时遗留 `running` 记录会标记为 `error.registration.interrupted`。

## 失败路径验收

建议至少人工验证：

- Gmail app password 错误时落库 `error.registration.mail_login_failed`。
- 未收到邮件时落库 `error.registration.mail_timeout`。
- 目标站点无法访问时落库 `error.registration.matuya_request_failed`。
- 目标表单结构变化时落库 `error.registration.matuya_form_changed`。
- 缺少 CSRF token 的 POST 返回 `400 error.csrf.invalid`。

## `matuya_request_failed` 排查

日志中出现 `NameResolutionError`、`Failed to resolve`、`Temporary failure in name resolution` 时，注册流程还没有进入 Gmail 收信阶段，而是第一步访问 Matuya 注册入口失败。按以下顺序排查：

1. 在宿主机确认 Matuya 主机名能解析：

```bash
python3 - <<'PY'
import socket
for host in ["替换为 Matuya URL 的主机名", "imap.gmail.com"]:
    try:
        print(host, socket.getaddrinfo(host, 443)[0][4])
    except Exception as exc:
        print(host, type(exc).__name__, exc)
PY
```

2. 在容器内确认 Docker 网络能解析：

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

3. 对照结果处理：

- 宿主机和容器都无法解析 Matuya 主机名，但可以解析 `imap.gmail.com`：优先核对 `MATUYA_REGISTER_URL` 和 `MATUYA_FORM_URL` 是否抄错、过期，或是否需要授权方提供新的注册入口；如果目标站点限制日本出口 IP，需要切换到允许的日本网络后重试。
- 宿主机可以解析但容器不能解析：检查 Docker DNS、代理、VPN 或公司网络策略；必要时在 `docker-compose.yml` 的 `app` 服务中配置可用的 `dns`。
- Matuya 主机名可以解析但请求超时或返回 4xx/5xx：检查 URL 路径、授权状态、目标站点可用性、出口 IP 地区限制和 `HTTP_TIMEOUT_SECONDS`。

## 运维注意事项

- `gunicorn` 当前配置为 2 个 worker。每个 worker 有自己的进程内线程池，实际并发上限可能是 worker 数乘以 `BATCH_MAX_WORKERS`。
- 进程内任务不持久化。容器重启会中断正在执行的任务，启动时会把残留 `running` 标为失败。
- 若未来需要严格全局并发或任务可靠性，应替换为外部队列。
- 账号密码明文保存在数据库中，应限制数据库、备份和宿主机访问。
- 自动化注册行为必须处在授权、合规和目标站点允许的范围内。
