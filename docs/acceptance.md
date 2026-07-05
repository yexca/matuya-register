# Acceptance And Handover

Date: 2026-07-05

## Completed Automated Checks

- `python -m pytest -q`: 45 passed.
- `docker compose build`: succeeded.
- `docker compose up -d` with `.env.example` copied to a temporary `.env`: succeeded.
- `GET http://localhost:8926/login` in the Compose container: returned `200 OK`.
- Container logs showed gunicorn listening on `0.0.0.0:8926`.

The local Python test run emits a `urllib3` LibreSSL warning on this macOS Python
3.9 installation. It does not fail the test suite.

## Functional Coverage

- Initial administrator creation is covered by tests.
- Unauthenticated page/API behavior is covered by tests.
- Login, logout, CSRF rejection, and locale switching are covered by tests.
- Account repository persistence, status updates, pagination, and copy counts are covered by tests.
- Generator, Matuya parser, mail parser, service success path, and main failure paths are covered by offline tests.
- API registration, batch validation, account lookup, copy count update, and localized errors are covered by tests.
- Docker image builds with `python:3.12-slim`, runs as a non-root user, exposes `8926`, and starts `wsgi:app` with gunicorn.

## Manual Checks Requiring Authorized Credentials

These items were not executed because no authorized external-service credentials
were provided:

- Real IMAP app-password login.
- Real registration mail delivery and polling.
- Real target registration submission.
- Real mail password error against the authorized mail service.
- Real mail timeout with production-like wait settings.
- Real target-site form-change behavior.

Use the conservative settings below for the first authorized run:

```text
BATCH_MAX_COUNT=5
BATCH_MAX_WORKERS=2
REGISTER_MAX_WAIT_SECONDS=90
REGISTER_POLL_INTERVAL_SECONDS=5
HTTP_TIMEOUT_SECONDS=20
```

## Handover Notes

- Registration tasks run in a process-local thread pool. Container restarts interrupt in-flight tasks.
- Startup marks leftover `pending` and `running` accounts as `error.registration.interrupted`.
- Account passwords are stored in plaintext to support the admin display/copy workflow. Protect `/data/app.db`, backups, and host access.
- `.env` is ignored by Git and Docker build context. Keep real secrets out of commits.
- SQLite defaults to `/data/app.db`; Docker Compose persists `/data` in the `matuya_data` volume.
- Automated tests are intentionally offline. Real external behavior must be validated manually within the authorized scope.

## Suggested Future Enhancements

- External task queue for durable background work.
- Retry policy with event history per registration stage.
- Password-at-rest encryption.
- CSV export for account history.
