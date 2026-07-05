# Getting Started

## Requirements

- Python 3.12 for local development.
- Docker and Docker Compose for container deployment.
- Authorized target registration URLs.
- One configured mail provider:
  - `gmail_imap`
  - `mail_tm`

## Prepare Configuration

Copy the sample file:

```bash
cp .env.example .env
```

Use obviously fake placeholders while developing documentation or tests:

```env
APP_SECRET_KEY=example-only-secret-do-not-use
ADMIN_USERNAME=example-admin-user
ADMIN_PASSWORD=example-admin-password-not-real
MATUYA_REGISTER_URL=https://matuya-register.example.invalid/register
MATUYA_FORM_URL=https://matuya-register.example.invalid/form

MAIL_PROVIDER=mail_tm
MAIL_PROVIDER_FALLBACK=
MAIL_TM_API_BASE=https://mail-api.example.invalid
MAIL_TM_SUFFIX=@mail-domain.example.invalid
```

For an authorized environment, replace placeholders with values supplied for that
environment. Never commit `.env`.

## Run With Docker Compose

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

## Run Locally

```bash
python -m venv .venv
. .venv/Scripts/activate
python -m pip install -r requirements.txt
```

Load environment variables in a shell-appropriate way, then run:

```bash
flask --app wsgi run --host 127.0.0.1 --port 8926
```

## Run Tests

```bash
python -m pytest -q
```

The automated tests are offline and use fake clients or fixtures. They must not
depend on live target sites or live mail services.
