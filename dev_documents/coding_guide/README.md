# Matuya 注册工具重写开发指导

本文档集用于指导 `matuya-register` 升级重写。开发阶段依据以下资料整理：

- `requirement/requirements-analysis.md`
- `high_design/high-level-design.md`
- `detail_design/detailed-design.md`
- 旧版 `matuya-register/` 中已验证的注册、邮件读取和页面交互逻辑

## 阶段顺序

| 阶段 | 文件 | 目标 |
| --- | --- | --- |
| 01 | `01_project_bootstrap.md` | 建立新项目骨架、依赖和运行入口 |
| 02 | `02_config_database.md` | 完成配置、SQLite、迁移和初始管理员数据 |
| 03 | `03_i18n_auth_security.md` | 完成 i18n、登录、Session、CSRF 和安全基础 |
| 04 | `04_account_domain_repository.md` | 完成账号领域对象、Repository、邮箱和密码生成 |
| 05 | `05_external_clients.md` | 完成 Matuya HTTP Client 和 Gmail IMAP Client |
| 06 | `06_registration_service_tasks.md` | 完成注册编排服务、任务执行器和失败归一化 |
| 07 | `07_routes_api_pages.md` | 完成页面、API、前端交互、轮询和复制统计 |
| 08 | `08_tests_quality.md` | 补齐离线测试、Mock、fixture 和质量门槛 |
| 09 | `09_docker_deployment.md` | 完成 Docker、Compose、环境样例和部署验证 |
| 10 | `10_acceptance_handover.md` | 完成端到端验收、风险检查和交付说明 |

## 开发原则

- 新版本不做旧代码平移，只复用旧系统已验证的外部行为。
- 路由层只处理 HTTP、权限、模板和响应，不直接写 SQL、调用 IMAP 或 requests。
- 业务编排放在 service，SQL 放在 repository，外部站点和邮件服务放在 client。
- 所有可变配置来自环境变量，真实密钥不得提交到代码仓库。
- 每次注册必须落库，成功、失败、复制次数和更新时间都可追踪。
- 自动测试默认不调用真实 Matuya 站点和 Gmail，外部交互通过 mock 或 fixture 验证。

## 使用方式

按阶段文件顺序实现。每个阶段完成后先执行该阶段验收，再进入下一阶段。若阶段中发现设计与现实代码冲突，以需求和详细设计为准，并在实现说明中记录调整原因。
