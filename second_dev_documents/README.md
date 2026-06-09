# Matuya Register 二次开发文档

本文档集面向后续维护者和二次开发者，基于 `dev_documents/` 的需求、概要设计、详细设计，以及 `matuya-register/` 的当前实现整理。

## 文档目录

| 文档 | 说明 |
| --- | --- |
| [architecture.md](architecture.md) | 应用架构、模块边界、注册流程和数据流 |
| [configuration.md](configuration.md) | 环境变量、启动校验、数据存储和安全配置 |
| [development-guide.md](development-guide.md) | 本地开发、代码约定、常见扩展点和变更建议 |
| [api-reference.md](api-reference.md) | 页面路由、JSON API、请求参数、响应结构和错误码 |
| [testing-and-deployment.md](testing-and-deployment.md) | 测试策略、Docker 部署、验收清单和运维注意事项 |

用户使用说明请查看应用目录下的英文 [README.md](../matuya-register/README.md) 和简体中文 [README.zh-cn.md](../matuya-register/README.zh-cn.md)。

## 项目定位

`matuya-register` 是一个轻量级 Flask 后台工具，用于在授权范围内发起 Matuya 注册流程，并跟踪每条账号记录的状态、失败原因、随机密码和邮箱复制次数。

系统不是旧版脚本的平移，而是按以下目标重写：

- 后台登录保护和 CSRF 防护。
- SQLite 持久化注册记录、管理员用户和复制次数。
- 邮箱唯一性由数据库唯一约束兜底。
- 注册、邮件、目标站点、数据库、页面路由分层隔离。
- 单容器 Docker Compose 部署。
- 默认英文界面，支持简体中文。

## 二次开发原则

- `routes` 只处理 HTTP、模板、权限和响应格式。
- `service` 负责编排业务流程和状态转换。
- `repository` 独占 SQL 和数据映射。
- `matuya` 与 `mail` 模块封装外部交互，便于替换和 mock。
- 配置全部来自环境变量，真实密钥不得写入代码或文档。
- 自动测试默认离线执行，不访问真实 Gmail 或 Matuya。

## 当前实现快照

主要运行入口：

```text
matuya-register/
  wsgi.py
  app/
    __init__.py
    config.py
    db.py
    i18n.py
    security.py
    auth/
    accounts/
    matuya/
    mail/
    templates/
    static/
    locales/
  migrations/
  tests/
  Dockerfile
  docker-compose.yml
```

主要技术栈：

- Python 3.12 Docker runtime
- Flask 3
- Jinja2 + 原生 JavaScript
- SQLite + 标准库 `sqlite3`
- `requests`
- `imaplib` + `email`
- BeautifulSoup4
- Faker
- Werkzeug password hash
- pytest

