# API 参考

所有 `/api/*` 路由都需要登录。POST 请求默认需要 CSRF token：

```http
X-CSRF-Token: <session csrf token>
Content-Type: application/json
```

页面模板会把 token 注入到：

```js
window.APP_CONFIG.csrfToken
```

## 页面路由

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/login` | 登录页面 |
| `POST` | `/login` | 提交管理员登录表单 |
| `POST` | `/logout` | 退出登录 |
| `GET` | `/` | 账号历史页面 |
| `POST` | `/locale` | 切换语言，支持 JSON 或表单 |

## `GET /api/accounts`

查询账号列表。

参数：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 空 | 可选 `pending`、`running`、`success`、`failed` |
| `page` | integer | `1` | 页码，最小 1 |
| `page_size` | integer | `PAGE_SIZE_DEFAULT` | 最大 `PAGE_SIZE_MAX` |

响应：

```json
{
  "items": [
    {
      "id": 1,
      "email": "user@example.com",
      "password": "Aa123456789012",
      "status": "success",
      "error_key": null,
      "error_message": "",
      "copy_count": 0,
      "last_copied_at": null,
      "created_at": "2026-06-09T00:00:00Z",
      "updated_at": "2026-06-09T00:00:00Z",
      "started_at": "2026-06-09T00:00:00Z",
      "completed_at": "2026-06-09T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

错误：

- `401 error.auth.required`
- `400 error.validation.status`
- `400 error.validation.pagination`

## `POST /api/register`

创建一条 `pending` 账号记录并提交后台注册任务。

请求体可以为空 JSON：

```json
{}
```

成功响应：`202 Accepted`

```json
{
  "account": {
    "id": 1,
    "email": "generated@example.com",
    "password": "Aa123456789012",
    "status": "pending",
    "error_key": null,
    "error_message": "",
    "copy_count": 0,
    "last_copied_at": null,
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:00Z",
    "started_at": null,
    "completed_at": null
  }
}
```

错误：

- `401 error.auth.required`
- `400 error.csrf.invalid`
- `409 error.registration.email_conflict_exhausted`

## `POST /api/register-batch`

批量创建账号并提交后台注册任务。

请求：

```json
{
  "count": 3
}
```

`count` 必须在 `1..BATCH_MAX_COUNT`。

成功响应：`202 Accepted`

```json
{
  "accounts": [
    {
      "id": 1,
      "email": "a@example.com",
      "password": "Aa123456789012",
      "status": "pending",
      "error_key": null,
      "error_message": "",
      "copy_count": 0,
      "last_copied_at": null,
      "created_at": "2026-06-09T00:00:00Z",
      "updated_at": "2026-06-09T00:00:00Z",
      "started_at": null,
      "completed_at": null
    }
  ]
}
```

错误：

- `400 error.validation.count`
- `409 error.registration.email_conflict_exhausted`

## `GET /api/accounts/<id>`

查询单条账号记录，通常用于前端轮询。

成功响应：

```json
{
  "account": {
    "id": 1,
    "email": "a@example.com",
    "password": "Aa123456789012",
    "status": "running",
    "error_key": null,
    "error_message": "",
    "copy_count": 0,
    "last_copied_at": null,
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:02Z",
    "started_at": "2026-06-09T00:00:01Z",
    "completed_at": null
  }
}
```

错误：

- `404 error.account.not_found`

## `POST /api/accounts/<id>/copy-account`

记录一次邮箱复制。密码复制不调用该接口，也不增加复制次数。

请求：

```json
{}
```

成功响应：

```json
{
  "account": {
    "id": 1,
    "email": "a@example.com",
    "password": "Aa123456789012",
    "status": "success",
    "error_key": null,
    "error_message": "",
    "copy_count": 1,
    "last_copied_at": "2026-06-09T00:00:05Z",
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:05Z",
    "started_at": "2026-06-09T00:00:01Z",
    "completed_at": "2026-06-09T00:00:04Z"
  }
}
```

错误：

- `404 error.account.not_found`

## `POST /locale`

切换界面语言。

请求：

```json
{
  "locale": "zh-CN"
}
```

成功响应：

```json
{
  "locale": "zh-CN"
}
```

表单提交时会重定向回来源页或首页。

错误：

- `400 error.locale.unsupported`
- `400 error.csrf.invalid`

## 稳定错误 key

| 错误 key | 说明 |
| --- | --- |
| `error.auth.required` | 未登录 |
| `error.csrf.invalid` | CSRF token 无效 |
| `error.locale.unsupported` | 不支持的语言 |
| `error.account.not_found` | 账号不存在 |
| `error.validation.count` | 批量数量无效 |
| `error.validation.pagination` | 分页参数无效 |
| `error.validation.status` | 状态筛选无效 |
| `error.registration.config_missing` | 注册配置缺失 |
| `error.registration.mail_login_failed` | 邮件服务登录失败 |
| `error.registration.mail_timeout` | 等待注册链接超时 |
| `error.registration.mail_parse_failed` | 邮件链接解析失败 |
| `error.registration.matuya_request_failed` | Matuya 请求失败 |
| `error.registration.matuya_form_changed` | 目标表单无法解析 |
| `error.registration.matuya_submit_failed` | Matuya 提交失败 |
| `error.registration.email_conflict_exhausted` | 生成唯一邮箱失败 |
| `error.registration.interrupted` | 任务被进程重启中断 |
| `error.registration.unknown` | 未归类异常 |

