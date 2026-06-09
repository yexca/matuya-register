# 阶段 07：页面、API 与前端交互

## 阶段目标

实现后台历史页面、账号注册 API、批量注册 API、状态轮询、复制账号统计和基础前端交互。此阶段完成后，管理员可以在浏览器中完成主要业务操作。

## 前置输入

- `requirement/requirements-analysis.md` 第 4.5、4.6、8、13 节。
- `detail_design/detailed-design.md` 第 15、16、17 章。
- 阶段 03 已完成登录、CSRF、i18n。
- 阶段 06 已完成 service 和任务执行。

## 产出文件

```text
app/accounts/routes.py
app/templates/base.html
app/templates/accounts.html
app/templates/partials/account_rows.html
app/static/app.css
app/static/app.js
```

## 开发任务

1. 实现页面路由：

- `GET /`：登录后展示账号历史、筛选和注册入口。

2. 实现 API：

```text
POST /api/register
POST /api/register-batch
GET /api/accounts
GET /api/accounts/<id>
POST /api/accounts/<id>/copy-account
```

3. API 通用要求：

- 必须登录。
- POST 必须校验 CSRF。
- 返回 JSON。
- 错误响应包含稳定 `error` 和本地化 `message`。
- `status` 参数只允许空、`pending`、`running`、`success`、`failed`。
- `page` 最小为 1。
- `page_size` 不超过 `PAGE_SIZE_MAX`。

4. 序列化账号：

- 返回 `id`、`email`、`password`、`status`。
- `error_key` 保存数据库中的错误 key。
- `error_message` 返回当前语言下的展示文案。
- 返回 `copy_count`、`last_copied_at`、`created_at`、`updated_at`、`started_at`、`completed_at`。

5. `accounts.html` 布局：

- 顶部栏：应用名、当前管理员、语言切换、退出登录。
- 操作区：单个注册按钮、批量数量输入、批量注册按钮。
- 筛选区：全部、等待中、注册中、成功、失败。
- 列表区：邮箱、密码、状态、失败原因、复制次数、最近复制时间、创建时间、更新时间、操作。
- 分页区：上一页、下一页、总数。

6. `app.js` 交互：

- 发起单个注册后立即插入新行。
- 发起批量注册后插入多行。
- 对 `pending` 和 `running` 记录轮询 `/api/accounts/<id>`。
- 记录变为 `success` 或 `failed` 后停止轮询。
- 全局最多同时轮询 20 条。
- 复制邮箱成功后再调用 `/api/accounts/<id>/copy-account`。
- 密码复制不计数。
- 所有动态文案从 `window.APP_CONFIG.messages` 获取。

7. 复制逻辑：

```text
navigator.clipboard.writeText
fallback: hidden textarea + document.execCommand("copy")
```

8. 页面状态：

- 提交中禁用按钮。
- API 失败显示本地化 message。
- 空列表显示空状态文案。
- 不把原始异常堆栈展示给用户。

## 设计约束

- 不引入大型前端框架。
- 不把页面写成旧版 `pages.py` 那种 Python 字符串。
- 路由不直接调用 `requests`、`imaplib` 或写 SQL。
- 前端不能信任输入，后端仍必须完整校验。

## 验收标准

- 登录后可打开 `/` 查看历史列表。
- `POST /api/register` 返回 `202` 和 pending 账号。
- `POST /api/register-batch` 返回多条 pending 账号，数量受配置限制。
- 页面能轮询状态直到 success 或 failed。
- 复制邮箱后 `copy_count` 刷新并持久化。
- 密码可复制但不增加账号复制次数。
- 状态筛选和分页可用。
- 中英文页面文案和 API 错误文案可切换。
