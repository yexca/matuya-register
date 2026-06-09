# 阶段 06：注册编排服务与任务执行器

## 阶段目标

实现账号注册的业务编排、线程池任务提交、状态转换、失败归一化和结构化日志。此阶段完成后，后台可以异步执行单个或批量注册任务，并把每条记录的最终状态落库。

## 前置输入

- `requirement/requirements-analysis.md` 第 4.4、4.5、5.5 节。
- `detail_design/detailed-design.md` 第 13、14、18、25 章。
- 阶段 04 已完成账号 Repository 和生成器。
- 阶段 05 已完成外部 client。

## 产出文件

```text
app/accounts/service.py
app/accounts/tasks.py
app/logging.py
```

## 开发任务

1. 实现 `TaskRunner`：

```python
submit(fn, *args, **kwargs)
shutdown()
```

2. 任务执行器要求：

- 使用 `ThreadPoolExecutor`。
- `max_workers` 来自 `BATCH_MAX_WORKERS`。
- 所有注册任务共享同一个线程池。
- `submit` 增加 done callback，记录未捕获异常。
- 应用退出时通过 `atexit` 调用 shutdown。

3. 实现 `AccountService`：

```python
enqueue_single_register(created_by)
enqueue_batch_register(count, created_by)
run_registration(account_id)
list_accounts(status, page, page_size)
get_account(account_id)
record_copy(account_id)
```

4. 创建唯一账号：

- 最多尝试 10 次。
- 每次生成新的 email 和 password。
- 调用 `repo.create_pending()`。
- 遇到 `DuplicateEmailError` 后重试。
- 重试耗尽抛 `EmailGenerateExhaustedError`。

5. 单个注册流程：

```text
pending -> running
send_register_mail
wait_register_link
generate_profile
complete_registration
running -> success
```

6. 任一步失败必须：

- 捕获异常。
- 归一化为错误 key。
- 更新状态为 `failed`。
- 写入 `completed_at` 和 `updated_at`。
- 记录详细异常日志。

7. 批量注册：

- 校验 `count` 在 `1..BATCH_MAX_COUNT`。
- 先创建全部 pending 记录。
- 再逐个提交线程池。
- 接口层之后应立即返回 account 列表，不等待任务完成。

8. 启动恢复：

- 应用启动时将上次遗留的 `running` 标记为 `failed`。
- 错误 key 使用 `error.registration.interrupted`。

9. 实现错误归一化：

| 异常 | error key |
| --- | --- |
| 配置缺失 | `error.registration.config_missing` |
| IMAP 登录失败 | `error.registration.mail_login_failed` |
| 邮件超时 | `error.registration.mail_timeout` |
| 邮件解析失败 | `error.registration.mail_parse_failed` |
| Matuya 请求失败 | `error.registration.matuya_request_failed` |
| Matuya 表单变化 | `error.registration.matuya_form_changed` |
| Matuya 提交失败 | `error.registration.matuya_submit_failed` |
| 邮箱冲突重试耗尽 | `error.registration.email_conflict_exhausted` |
| 其他异常 | `error.registration.unknown` |

## 日志要求

注册阶段日志至少包含：

```text
account_id
email
stage
status
duration_ms
error
```

建议阶段：

```text
create_account
send_register_mail
wait_register_link
generate_profile
complete_registration
complete
fail
```

日志不得包含 Gmail 密码、管理员密码、Session、CSRF token。

## 验收标准

- fake client 成功路径可让账号从 `pending` 变为 `success`。
- fake Mail 超时会让账号变为 `failed`，错误 key 正确。
- fake Matuya 表单错误会让账号变为 `failed`，错误 key 正确。
- 批量注册单条失败不影响其他记录。
- 任务接口返回时不阻塞等待全部注册完成。
- 应用启动后遗留 `running` 会被标记为 interrupted failure。
