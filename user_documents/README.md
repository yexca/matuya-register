# Matuya Register

Matuya Register is a lightweight Flask administrator tool for authorized Matuya registration workflows. It can start single or small batch registration tasks, read registration links from Gmail IMAP, complete the target registration form, and store each generated account with its status, password, failure reason, and email-copy count in SQLite.

This project is for authorized testing and maintenance only. Do not use it in ways that violate laws, website terms, account policies, or the target service owner's instructions.

Simplified Chinese README: [README.zh-cn.md](README.zh-cn.md)

## Features

- Administrator login and logout.
- English UI by default, with Simplified Chinese support.
- Single and small batch registration.
- Random unique email generation backed by a SQLite unique constraint.
- Random 14-character passwords with lowercase, uppercase, and digits.
- Registration history with status filters and pagination.
- Localized failure messages.
- Email and password copy actions.
- Persistent email-copy count.
- Docker Compose deployment with persistent SQLite storage.

## Requirements

- Docker and Docker Compose for deployment.
- Or Python 3.12 for local development.
- Authorized Matuya registration endpoints.
- Gmail account with IMAP enabled and an app password.

## Configuration

Copy the sample environment file:

```bash
cp .env.example .env
```

Edit `.env` before starting the app.

Required values:

| Variable | Description |
| --- | --- |
| `APP_SECRET_KEY` | Long random secret used by Flask sessions |
| `ADMIN_USERNAME` | Initial administrator username |
| `ADMIN_PASSWORD` | Initial administrator password |
| `MATUYA_REGISTER_URL` | Authorized Matuya registration entry URL |
| `MATUYA_FORM_URL` | Authorized Matuya form submit URL |
| `MAIL_USERNAME` | Gmail address used to read registration mail |
| `MAIL_PASSWORD` | Gmail app password |
| `MAIL_SUFFIX` | Suffix for generated email addresses, for example `@example.com` |

Important optional values:

| Variable | Default | Description |
| --- | --- | --- |
| `SQLITE_PATH` | `/data/app.db` | SQLite database path |
| `BATCH_MAX_COUNT` | `5` | Maximum accepted batch size |
| `BATCH_MAX_WORKERS` | `2` | Process-local registration worker threads |
| `REGISTER_MAX_WAIT_SECONDS` | `90` | Maximum time to wait for registration mail |
| `REGISTER_POLL_INTERVAL_SECONDS` | `5` | Mail polling interval |
| `HTTP_TIMEOUT_SECONDS` | `20` | Matuya HTTP request timeout |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` behind HTTPS |

Never commit `.env`, real Gmail app passwords, or production secrets.

## Run With Docker Compose

Build and start:

```bash
docker compose build
docker compose up -d
```

Open:

```text
http://localhost:8926
```

Follow logs:

```bash
docker compose logs -f app
```

Stop:

```bash
docker compose down
```

## Use The Admin UI

1. Sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
2. Click **Register one** to start a single registration task.
3. Enter a count and click **Batch register** to start a small batch.
4. Use the status filters to view pending, running, successful, or failed records.
5. Copy the generated email or password from the history table.

The page polls running tasks automatically. Email copies are counted; password copies are not.

## SQLite Data

The container stores SQLite at:

```text
/data/app.db
```

`docker-compose.yml` mounts `/data` to the named volume `matuya_data`, so history and copy counts survive container restarts.

Back up the database:

```bash
docker compose exec app sh -c 'cp /data/app.db /data/app.db.backup'
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /data/app.db /backup/app.db
```

Restore only after stopping the app:

```bash
docker compose down
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /backup/app.db /data/app.db
docker compose up -d
```

## Local Development

Install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest -q
```

Run locally:

```bash
export $(grep -v '^#' .env | xargs)
flask --app wsgi run --host 127.0.0.1 --port 8926
```

## Operational Notes

- Registration tasks run in a process-local `ThreadPoolExecutor`.
- Restarting the app interrupts running tasks; startup marks leftover `running` records as `error.registration.interrupted`.
- Account passwords are stored in plaintext because the admin UI must display and copy them. Protect the database file, backups, and deployment host.
- Automated tests use fakes and fixtures. Real Matuya and Gmail validation must be performed manually with authorization.

