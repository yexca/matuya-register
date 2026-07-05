# Architecture

## Module Map

```text
app/
  __init__.py          Flask app factory
  config.py            environment parsing and validation
  db.py                SQLite connection and migrations
  i18n.py              locale selection and message lookup
  security.py          CSRF and current-user helpers
  auth/                administrator login
  accounts/            account routes, service, repository, task runner
  matuya/              target registration HTTP client
  mail/                mail providers, IMAP client, temporary-mail client, parser
  templates/           server-rendered pages
  static/              browser JavaScript and CSS
migrations/            SQLite migrations
tests/                 offline tests
```

Routes handle HTTP concerns only. Business orchestration belongs in
`AccountService`. SQL belongs in repositories. Target-site and mail-service calls
belong in clients.

## Registration Flow

```text
POST /api/register
  -> AccountService.enqueue_single_register()
  -> create a provider-backed email address
  -> create a pending SQLite record
  -> submit a background task

background task
  -> mark account running
  -> send target registration mail
  -> wait for registration link through the configured mail provider
  -> generate profile data
  -> complete target registration form
  -> mark account success or failed
```

## Mail Provider Flow

`app/mail/providers.py` exposes a fallback provider wrapper. The configured
providers are tried in order while preparing a new recipient address.

```text
MAIL_PROVIDER=mail_tm
MAIL_PROVIDER_FALLBACK=gmail_imap
```

With that configuration, the app first tries to create and prepare a
mail.tm-compatible temporary mailbox. If that preparation fails, it tries Gmail
IMAP with a newly generated address.

Once a registration message has been requested for an address, fallback does not
move that already-sent message to another provider.

## Data Model

The main table is `matuya_accounts`.

| Field | Purpose |
| --- | --- |
| `email` | Generated target login email. Unique. |
| `password` | Generated target login password. Stored for admin display. |
| `status` | `pending`, `running`, `success`, or `failed`. |
| `error_message` | Stable error key. |
| `copy_count` | Number of successful email copy actions. |
| `created_by` | Administrator user id. |
| `started_at` / `completed_at` | Registration task timing. |

Passwords are stored in plaintext because the admin UI must display and copy
them. Protect the database and backups accordingly.

## Error Normalization

Low-level exceptions are normalized to stable keys such as:

```text
error.registration.mail_timeout
error.registration.mail_service_failed
error.registration.matuya_form_changed
error.registration.email_conflict_exhausted
```

The database stores the key. The UI and API translate that key for the current
locale.
