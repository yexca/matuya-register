# 阶段 09：Docker 与部署配置

## 阶段目标

完成单容器部署能力，提供 Dockerfile、Compose、环境样例、忽略规则和基础运行说明。此阶段完成后，维护者可以通过 Docker Compose 启动应用，并将 SQLite 数据持久化到 volume。

## 前置输入

- `requirement/requirements-analysis.md` 第 5.2 节。
- `high_design/high-level-design.md` 第 13 章。
- `detail_design/detailed-design.md` 第 20、21 章。
- 阶段 01 至 08 已完成应用和测试。

## 产出文件

```text
Dockerfile
docker-compose.yml
.dockerignore
.env.example
README.md
```

## 开发任务

1. 编写 `Dockerfile`：

- 基础镜像使用 `python:3.12-slim`。
- 设置 `PYTHONDONTWRITEBYTECODE=1`。
- 设置 `PYTHONUNBUFFERED=1`。
- 创建非 root 用户。
- 安装 `requirements.txt`。
- 创建 `/data` 并赋权。
- 暴露 `8926`。
- 使用 gunicorn 启动 `wsgi:app`。

2. 编写 `docker-compose.yml`：

```yaml
services:
  app:
    build: .
    ports:
      - "8926:8926"
    env_file:
      - .env
    volumes:
      - matuya_data:/data
    restart: unless-stopped

volumes:
  matuya_data:
```

3. 编写 `.dockerignore`：

```text
.git
.venv
__pycache__
.pytest_cache
.env
*.pyc
```

4. 更新 `.env.example`：

- 包含全部配置项。
- 所有密钥使用示例值。
- 不写真实 Gmail app password。
- 不写真实 Matuya 地址，除非用户确认可以公开。

5. 更新 `README.md`：

- 项目用途和免责声明。
- 配置说明。
- Docker Compose 启动方式。
- SQLite 数据位置。
- 如何查看日志。
- 如何备份 volume 或 `/data/app.db`。
- 测试命令。

6. 部署运行检查：

```bash
docker compose build
docker compose up -d
docker compose logs -f app
```

7. 容器内数据要求：

- 默认 SQLite 路径为 `/data/app.db`。
- `/data` 由 volume 持久化。
- 容器重启后历史记录和复制次数仍然保留。

## 安全注意事项

- `.env` 必须被忽略。
- `APP_SECRET_KEY` 应使用长随机字符串。
- Gmail 使用 app password，不使用个人账户登录密码。
- HTTPS 反代部署时设置 `SESSION_COOKIE_SECURE=true`。
- 日志不得输出敏感配置。

## 验收标准

- `docker compose build` 成功。
- `docker compose up -d` 后应用监听 `8926`。
- 首次启动会创建管理员。
- 未登录访问后台跳转登录页。
- 容器重启后数据库文件和历史记录仍在。
- `.env` 不会被 Docker build context 或 Git 提交。
