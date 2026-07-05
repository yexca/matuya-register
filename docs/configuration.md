# Configuration

Configuration is loaded from environment variables in `app/config.py`. Startup
fails with `ConfigError` when required values are missing or malformed.

## Core Variables

| Variable | Required | Example | Description |
| --- | --- | --- | --- |
| `APP_SECRET_KEY` | yes | `not-a-real-secret-change-me` | Flask session secret. |
| `ADMIN_USERNAME` | yes | `fake-admin` | Initial administrator username. |
| `ADMIN_PASSWORD` | yes | `fake-password` | Initial administrator password. |
| `SQLITE_PATH` | no | `./data/app.db` | SQLite database path. |
| `MATUYA_REGISTER_URL` | yes | `https://matuya-register.example.invalid/register` | Authorized registration page. |
| `MATUYA_FORM_URL` | yes | `https://matuya-register.example.invalid/form` | Authorized registration form endpoint. |

## Mail Provider Selection

| Variable | Required | Example | Description |
| --- | --- | --- | --- |
| `MAIL_PROVIDER` | no | `mail_tm` | Primary provider. Defaults to `gmail_imap`. |
| `MAIL_PROVIDER_FALLBACK` | no | `gmail_imap` | Optional fallback provider list. |

Provider names are comma-friendly and normalized to lowercase underscores. These
are equivalent:

```env
MAIL_PROVIDER=mail-tm
MAIL_PROVIDER_FALLBACK=gmail_imap
```

```env
MAIL_PROVIDER=mail_tm
MAIL_PROVIDER_FALLBACK=gmail_imap
```

Fallback only applies while creating and preparing a new recipient address. If a
message has already been requested for one address, the app cannot receive that
same message through a different provider.

## Gmail IMAP Provider

Required when `MAIL_PROVIDER` or `MAIL_PROVIDER_FALLBACK` includes
`gmail_imap`:

| Variable | Example | Description |
| --- | --- | --- |
| `MAIL_IMAP_HOST` | `imap.gmail.com` | IMAP host. |
| `MAIL_IMAP_PORT` | `993` | IMAP SSL port. |
| `MAIL_USERNAME` | `fake-mailbox@gmail.com` | IMAP login username. |
| `MAIL_PASSWORD` | `fake-mail-password` | IMAP login password or app password. |
| `MAIL_SUFFIX` | `@gmail.com` | Suffix for generated target addresses. |

## Mail.tm-Compatible Provider

Required when `MAIL_PROVIDER` or `MAIL_PROVIDER_FALLBACK` includes `mail_tm`:

| Variable | Example | Description |
| --- | --- | --- |
| `MAIL_TM_API_BASE` | `https://mail-api.example.invalid` | Base URL for the temporary-mail API. |
| `MAIL_TM_SUFFIX` | `@mail-domain.example.invalid` | Suffix used when generating temporary addresses. |
| `MAIL_TM_CLEANUP_ACCOUNT` | `false` | Whether to delete the temporary mailbox after cleanup is requested. |

`MAIL_TM_SUFFIX` is the only supported way to configure the mail.tm-compatible
address suffix.

## Registration Timing

| Variable | Default | Description |
| --- | --- | --- |
| `REGISTER_MAX_WAIT_SECONDS` | `90` | Maximum time to wait for a registration email. |
| `REGISTER_POLL_INTERVAL_SECONDS` | `5` | Mail polling interval. |
| `HTTP_TIMEOUT_SECONDS` | `20` | HTTP timeout for target-site and mail-provider requests. |

## Batch And UI Limits

| Variable | Default | Description |
| --- | --- | --- |
| `BATCH_MAX_COUNT` | `5` | Maximum batch size accepted by the API. |
| `BATCH_MAX_WORKERS` | `2` | Local worker thread count. |
| `PAGE_SIZE_DEFAULT` | `20` | Default account-list page size. |
| `PAGE_SIZE_MAX` | `50` | Maximum account-list page size. |

## Security And Locale

| Variable | Default | Description |
| --- | --- | --- |
| `ENABLE_CSRF` | `true` | Enables CSRF checks for POST requests. |
| `DEFAULT_LOCALE` | `en` | Default UI locale. |
| `SUPPORTED_LOCALES` | `en,zh-CN` | Runtime locale list. |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` behind HTTPS. |
| `SESSION_LIFETIME_DAYS` | `30` | Session lifetime. |
