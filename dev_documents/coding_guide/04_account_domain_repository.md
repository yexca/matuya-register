# 阶段 04：账号领域、Repository 与生成器

## 阶段目标

实现 Matuya 账号记录的数据模型、Repository、邮箱唯一创建、随机密码和注册资料生成。此阶段完成后，系统可以离线创建 pending 账号记录、查询历史、更新状态和记录复制次数。

## 前置输入

- `requirement/requirements-analysis.md` 第 4.2、4.3、4.6、5.3 节。
- `detail_design/detailed-design.md` 第 6、7、10、17 章。
- 阶段 02 已完成数据库迁移。

## 产出文件

```text
app/accounts/types.py
app/accounts/repository.py
app/accounts/generator.py
app/matuya/types.py
```

## 开发任务

1. 定义账号状态枚举：

```python
pending
running
success
failed
```

2. 定义领域对象：

- `Account`
- `Page`
- `CopyResult`
- `RegistrationResult`
- `RegistrationProfile`

3. 实现 `AccountRepository`：

```python
create_pending(email, password, created_by)
get(account_id)
list(status, page, page_size)
mark_running(account_id)
mark_success(account_id)
mark_failed(account_id, error_message)
increment_copy_count(account_id)
mark_interrupted_running_accounts()
```

4. Repository 规则：

- SQL 只写在 repository 中。
- 插入重复 email 时抛出明确的 `DuplicateEmailError`。
- `mark_running` 只允许从 `pending` 或 `failed` 进入 `running`。
- `mark_failed` 写入错误 key，最多保留 500 字符。
- `increment_copy_count` 必须在数据库中原子递增。

5. 实现 `AccountGenerator`：

- 使用 `Faker("en_US")` 生成英文名。
- 邮箱格式为 `{first_name}{birth_date}{token}{MAIL_SUFFIX}`。
- 本地部分转小写，只保留字母和数字。
- 随机 token 使用 `secrets.token_hex(3)`。
- 密码默认 14 位。
- 密码使用 `secrets.choice`。
- 密码至少包含一个小写字母、一个大写字母、一个数字。
- MVP 不加入符号，降低目标站点表单兼容风险。

6. 实现注册资料生成：

- 姓名使用 Faker。
- 假名字段 MVP 沿用英文名。
- 电话前缀从 `070`、`080`、`090` 选择。
- 后两段电话为 4 位数字。

## 设计要点

邮箱唯一性不要靠“生成后查询”。正确流程是：

1. 生成器只负责生成候选邮箱。
2. Repository 插入 `pending` 记录。
3. SQLite 唯一索引保证并发下不重复。
4. 如果出现唯一冲突，由 service 重试生成。

## 验收标准

- 可创建 `pending` 账号，邮箱唯一且密码随机。
- 重复 email 会触发唯一冲突错误。
- 列表支持状态筛选、分页和按创建时间倒序。
- 状态更新会维护 `started_at`、`completed_at`、`updated_at`。
- 复制账号后 `copy_count` 持久化递增。
- 生成密码长度正确，且包含大小写字母和数字。
- 生成邮箱总是以配置的 `MAIL_SUFFIX` 结尾。
