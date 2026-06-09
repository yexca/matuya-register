# 阶段 10：端到端验收与交付

## 阶段目标

完成上线前的人工验收、真实配置验证、风险复查和交付说明。此阶段确认 MVP 满足需求分析、概要设计和详细设计中的验收项。

## 前置输入

- 阶段 01 至 09 已完成。
- 已准备授权测试使用的 Matuya 配置和 Gmail app password。
- 已确认测试行为符合目标站点条款和授权范围。

## 验收准备

1. 准备 `.env`：

```text
APP_SECRET_KEY
ADMIN_USERNAME
ADMIN_PASSWORD
MATUYA_REGISTER_URL
MATUYA_FORM_URL
MAIL_USERNAME
MAIL_PASSWORD
MAIL_SUFFIX
```

2. 设置保守批量配置：

```text
BATCH_MAX_COUNT=5
BATCH_MAX_WORKERS=2
REGISTER_MAX_WAIT_SECONDS=90
REGISTER_POLL_INTERVAL_SECONDS=5
HTTP_TIMEOUT_SECONDS=20
```

3. 启动应用：

```bash
docker compose up -d
docker compose logs -f app
```

## 功能验收

逐项确认：

- Docker Compose 可以启动应用。
- 首次启动根据环境变量创建管理员。
- 未登录访问 `/` 会跳转 `/login`。
- 未登录访问 `/api/accounts` 返回 `401`。
- 管理员可以登录和登出。
- 浏览器语言为简中时显示简中，否则默认英语。
- 页面可手动切换英语和简中。
- 登录后可以发起单个注册。
- 注册过程中历史列表显示 `pending` 或 `running`。
- 注册成功后历史列表展示邮箱、随机密码、状态和时间。
- 注册失败时状态为 `failed`，并展示本地化失败原因。
- 点击复制邮箱后复制次数递增。
- 复制次数在刷新页面和重启容器后仍然保留。
- 密码可以复制，但不增加邮箱复制次数。
- 批量注册数量受 `BATCH_MAX_COUNT` 限制。
- 实际并发受 `BATCH_MAX_WORKERS` 限制。
- 多次注册不会出现重复邮箱。
- Gmail、Matuya 地址和邮箱后缀没有硬编码在代码中。
- SQLite 数据通过 Docker volume 持久化。

## 失败路径验收

至少人工验证以下失败情况：

- Gmail 密码错误时显示邮件服务登录失败。
- 邮件等待超时时显示未收到注册链接。
- Matuya 页面 HTML fixture 缺少 form 时 parser 测试失败。
- 缺少 CSRF token 的 POST API 返回 `400`。
- 批量数量超过上限时返回参数错误。
- 容器在 running 任务期间重启后，遗留任务被标记为 interrupted failure。

## 日志验收

容器日志应能看到：

- account_id
- email
- stage
- status
- duration_ms
- failed 阶段的异常详情

日志不得出现：

- Gmail app password
- 管理员密码
- Session cookie
- CSRF token

## 交付说明

交付时应说明：

- MVP 使用进程内线程池，容器重启会中断正在运行的任务。
- Matuya 账号密码因后台展示需求以明文保存，应保护数据库文件和部署环境。
- 自动测试不访问真实外部服务，真实注册链路需要人工授权测试。
- 后续增强可加入任务队列、失败重试、事件明细、密码字段加密和 CSV 导出。

## 最终验收标准

- `pytest` 全部通过。
- Docker Compose 可启动并持久化数据。
- 管理员后台主要流程可用。
- 单个注册、批量注册、历史查询、状态筛选、复制统计均符合需求。
- 失败原因落库并可在页面查看。
- 配置、密钥和部署说明满足安全默认值要求。
