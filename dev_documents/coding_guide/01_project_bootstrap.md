# 阶段 01：项目骨架与运行入口

## 阶段目标

建立重写版本的基础工程结构，让项目具备清晰分层、可导入、可启动的最小 Flask 应用骨架。此阶段不实现真实注册链路，只完成目录、依赖、入口和基础约束。

## 前置输入

- 参考旧版 `matuya-register/app.py` 的 Flask 入口。
- 参考 `detail_design/detailed-design.md` 第 3、20、21 章。

## 产出文件

在 `matuya-register/` 下建立或调整：

```text
app/
  __init__.py
  config.py
  db.py
  i18n.py
  logging.py
  security.py
  auth/
    __init__.py
    decorators.py
    repository.py
    routes.py
    service.py
  accounts/
    __init__.py
    generator.py
    repository.py
    routes.py
    service.py
    tasks.py
    types.py
  matuya/
    __init__.py
    client.py
    exceptions.py
    parser.py
    types.py
  mail/
    __init__.py
    exceptions.py
    imap_client.py
    parser.py
  templates/
  static/
  locales/
migrations/
tests/
wsgi.py
requirements.txt
```

## 开发任务

1. 保留旧版代码作为参考，但新功能放入新目录结构。
2. 创建 `wsgi.py`，只负责导入并创建 Flask app：

```python
from app import create_app

app = create_app()
```

3. 在 `app/__init__.py` 中实现 `create_app()` 的空骨架：

- 创建 Flask 实例。
- 加载配置对象。
- 设置 `app.secret_key`。
- 初始化日志、数据库、安全钩子、蓝图和模板 helper。
- 不在 import 阶段连接 Gmail 或访问 Matuya。

4. 在 `requirements.txt` 中准备 MVP 依赖：

```text
Flask>=3.0,<4
gunicorn>=22,<24
requests>=2.31,<3
beautifulsoup4>=4.12,<5
Faker>=25,<40
Werkzeug>=3.0,<4
pytest>=8,<9
```

5. 为每个包补充 `__init__.py`，保证测试和应用入口可稳定导入。

## 约束

- 不要把旧版 `pages.py` 的长字符串 HTML 迁移到新版本。
- 不要在路由里直接编排完整注册逻辑。
- 不要在应用启动时真实访问外部网络。
- 当前阶段只追求项目可以导入和启动，不要求页面完整。

## 验收标准

- `python -c "from app import create_app; app = create_app(); print(app.name)"` 可以运行。
- `python -c "import wsgi; print(wsgi.app.name)"` 可以运行。
- 目录结构与详细设计保持一致，后续阶段无需再次大规模移动文件。
- 旧版业务行为的参考文件仍可查阅，没有被误删。
