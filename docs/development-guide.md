# Development Guide

## Principles

- Keep routes thin.
- Keep business flow in services.
- Keep SQL in repositories.
- Keep external HTTP, IMAP, and mail-provider calls in clients.
- Do not contact target services, mail services, or external databases at import
  time.
- Keep automated tests offline by default.

## Adding A Mail Provider

Implement the provider shape used in `app/mail/providers.py`:

```python
class ExampleProvider:
    name = "example_provider"

    def generate_email(self):
        return "fake-user@mail-domain.example.invalid"

    def prepare_recipient(self, recipient):
        return None

    def wait_register_link(self, recipient):
        return "https://registration-link.example.invalid/complete/fake-token"

    def cleanup_recipient(self, recipient):
        return None

    def can_handle(self, recipient):
        return recipient.endswith("@mail-domain.example.invalid")
```

Then:

1. Add configuration fields in `app/config.py`.
2. Register the provider in `create_mail_provider()`.
3. Map provider failures to existing `app.mail.exceptions` classes.
4. Add offline tests with fake sessions or fake provider objects.
5. Update [Configuration](configuration.md).

## Updating Target-Site Form Logic

Target-site form behavior lives in `app/matuya/client.py` and parser helpers.
When form fields change:

1. Add or update an HTML fixture.
2. Adjust parser or payload logic.
3. Add tests for the new fixture.
4. Verify manually only in an authorized environment.

Use fake URLs in fixtures, for example:

```text
https://matuya-register.example.invalid/form
```

## Error Handling

Add new stable error keys only when existing keys cannot describe the failure.
When adding a key:

1. Raise or map a typed exception.
2. Update `normalize_registration_error()`.
3. Add locale entries.
4. Add tests for the failure path.

## Testing

Run:

```bash
python -m pytest -q
```

Tests should not use live services. Use fake clients and fake API bases such as:

```text
https://mail-api.example.invalid
https://matuya-register.example.invalid
```
