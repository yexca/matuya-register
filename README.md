# Matuya Register

Matuya Register is a Flask-based administrator tool for creating and tracking Matuya registration attempts. It stores every account, status transition, failure key, and email-copy count in SQLite.

This project is for authorized testing and maintenance workflows only. Do not use it in ways that violate laws, account policies, website terms, or the target service owner's instructions.

## Configuration

Copy `.env.example` to `.env` and set deployment-specific values:

```bash
cp .env.example .env
```

Required values:

- `APP_SECRET_KEY`: long random secret used by Flask sessions.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`: initial administrator credentials.
- `MATUYA_REGISTER_URL` / `MATUYA_FORM_URL`: authorized target registration endpoints.
- `MAIL_USERNAME` / `MAIL_PASSWORD`: Gmail address and app password used to read registration mail.
- `MAIL_SUFFIX`: suffix used when generating account email addresses.

Important optional values:

- `SQLITE_PATH`: defaults to `/data/app.db` for Docker volume persistence.
- `BATCH_MAX_COUNT`: maximum batch size accepted by the API.
- `BATCH_MAX_WORKERS`: process-local registration worker threads.
- `REGISTER_MAX_WAIT_SECONDS`: maximum time to wait for registration mail.
- `SESSION_COOKIE_SECURE`: set to `true` when the app is served behind HTTPS.

Never commit `.env` or real Gmail app passwords.

## Docker Compose

Build and start the app:

```bash
docker compose build
docker compose up -d
```

Open the administrator UI at:

```text
http://localhost:8926
```

Follow logs:

```bash
docker compose logs -f app
```

Stop the app:

```bash
docker compose down
```

## SQLite Data

The container stores SQLite at `/data/app.db`. `docker-compose.yml` mounts `/data` to the named volume `matuya_data`, so history and copy counts survive container restarts.

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

Install dependencies and run tests:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
```

Run locally without Docker:

```bash
export $(grep -v '^#' .env | xargs)
flask --app wsgi run --host 127.0.0.1 --port 8926
```

## Operational Notes

- Registration tasks run in a process-local `ThreadPoolExecutor`.
- Restarting the app interrupts running tasks; startup marks leftover `running` records as `error.registration.interrupted`.
- Account passwords are stored in plaintext because the admin UI must display and copy them. Protect the database file and deployment host.
- Automated tests use fakes and fixtures. Real Matuya/Gmail validation must be performed manually with authorization.
