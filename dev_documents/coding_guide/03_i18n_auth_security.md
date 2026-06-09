# 阶段 03：i18n、认证与安全基础

## 阶段目标

实现后台登录保护、Session、CSRF、语言识别和中英文文案资源。完成后，未登录用户无法访问后台页面和 API，界面默认英语并可按浏览器语言切换到简中。

## 前置输入

- `detail_design/detailed-design.md` 第 8、9、15、19 章。
- 阶段 02 已完成数据库和初始管理员。

## 产出文件

```text
app/i18n.py
app/security.py
app/auth/decorators.py
app/auth/routes.py
app/auth/service.py
app/locales/en.json
app/locales/zh-CN.json
app/templates/base.html
app/templates/login.html
```

## 开发任务

1. 实现 `I18n`：

- 加载 `app/locales/en.json` 和 `app/locales/zh-CN.json`。
- 启动时校验两份资源 key 集合一致。
- 语言选择优先级为 query 参数、Session、`Accept-Language`、默认语言。
- 将 `zh`、`zh-CN`、`zh-Hans` 归一化为 `zh-CN`。
- 将 `en`、`en-US` 等归一化为 `en`。

2. 在模板上下文注入：

```python
locale
supported_locales
t(key, **kwargs)
i18n_catalog
csrf_token
```

3. 实现认证服务：

- `ensure_initial_admin(username, password)`
- `login(username, password)`
- `get_current_user(user_id)`

4. 密码处理使用 Werkzeug：

```python
generate_password_hash()
check_password_hash()
```

5. 实现登录路由：

- `GET /login`
- `POST /login`
- `POST /logout`

6. 实现登录保护装饰器：

- 页面请求未登录时跳转 `/login`。
- API 请求未登录时返回 `401`。

7. 实现 CSRF：

- Session 中保存 `csrf_token`。
- `POST` 表单从 `_csrf_token` 读取。
- JSON API 从 `X-CSRF-Token` 读取。
- 使用 `secrets.compare_digest` 比较。
- `ENABLE_CSRF=false` 时允许测试环境关闭。

8. 实现 `POST /locale`：

- 校验 CSRF。
- 只允许 `en` 和 `zh-CN`。
- 写入 `session["locale"]`。
- JSON 请求返回 `{ "locale": "..." }`，表单请求跳回来源页。

9. 设置 Session Cookie：

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
```

## 文案要求

- `en.json` 是主资源，新增 key 先加英语。
- `zh-CN.json` 必须包含完全相同的 key。
- API 错误响应同时返回稳定 `error` 和本地化 `message`。
- 模板中不要硬编码业务文案，统一使用 `t("...")`。

## 验收标准

- 未登录访问 `/` 跳转 `/login`。
- 未登录访问 `/api/accounts` 返回 `401`。
- 正确管理员账号密码可以登录。
- 错误账号密码不暴露用户是否存在。
- 登出后不能继续访问后台。
- 缺少 CSRF 的 POST API 返回 `400`。
- 浏览器语言为 `zh-CN` 时页面显示简中，否则默认英语。
- `POST /locale` 可手动切换语言。
