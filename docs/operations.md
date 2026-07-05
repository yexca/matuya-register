# Operations

## Deployment Checklist

Before deployment, verify:

- `.env` exists and is not committed.
- All placeholder values have been replaced for the authorized environment.
- `APP_SECRET_KEY` is long and random.
- `ADMIN_PASSWORD` is strong.
- The selected mail provider is reachable from the deployment network.
- `SESSION_COOKIE_SECURE=true` is set behind HTTPS.

## Docker Compose

Build and start:

```bash
docker compose build
docker compose up -d
```

View logs:

```bash
docker compose logs -f app
```

Stop:

```bash
docker compose down
```

## SQLite Persistence

The default container database path is:

```text
/data/app.db
```

The Compose file mounts `/data` to a named volume. Back up that database before
upgrades or operational experiments.

Example backup with fake local filenames:

```bash
docker compose exec app sh -c 'cp /data/app.db /data/fake-backup.db'
docker run --rm -v matuya-register_matuya_data:/data -v "$PWD":/backup busybox cp /data/app.db /backup/fake-app.db
```

## Troubleshooting

### App Fails At Startup

Check configuration errors first:

```bash
docker compose logs app
```

Common causes:

- Missing required environment variables.
- `MAIL_TM_SUFFIX` does not start with `@`.
- `MAIL_TM_API_BASE` is not an absolute HTTP URL.
- Gmail provider selected without complete IMAP settings.

### Registration Stays Running

The browser polls running tasks. If the app restarts while tasks are active,
startup marks leftover `running` rows as:

```text
error.registration.interrupted
```

### Mail Does Not Arrive

Check:

- The configured provider matches the generated address suffix.
- `REGISTER_MAX_WAIT_SECONDS` is long enough for the authorized environment.
- The target site accepted the address.
- The mail provider was reachable from the container.

### Target Form Changed

Form parse or submit failures normally appear as:

```text
error.registration.matuya_form_changed
error.registration.matuya_submit_failed
```

Update fixtures and `app/matuya/client.py` before retesting.
