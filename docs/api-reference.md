# API Reference

All API routes require an authenticated administrator session unless noted.
POST routes require a valid CSRF token when CSRF is enabled.

## `POST /api/register`

Starts one registration task.

Response:

```json
{
  "account": {
    "id": 101,
    "email": "fake-user@mail-domain.example.invalid",
    "password": "Aa123456789012",
    "status": "pending",
    "raw_status": "pending",
    "bucket": "unused",
    "error_key": null,
    "error_message": "",
    "copy_count": 0,
    "email_copy_count": 0,
    "password_copy_count": 0
  }
}
```

## `POST /api/register-batch`

Starts a small batch of registration tasks.

Request:

```json
{
  "count": 3
}
```

Response:

```json
{
  "accounts": [
    {
      "id": 201,
      "email": "fake-one@mail-domain.example.invalid",
      "password": "Aa123456789012",
      "status": "pending"
    }
  ]
}
```

## `GET /api/accounts`

Lists accounts.

Query parameters:

| Parameter | Example | Description |
| --- | --- | --- |
| `status` | `success` | Optional status filter. |
| `bucket` | `unused` | Optional UI bucket filter: `unused`, `used`, or `failed`. Defaults to `unused`. |
| `page` | `1` | Page number. |
| `page_size` | `20` | Page size. |

Response:

```json
{
  "items": [
    {
      "id": 301,
      "email": "fake-history@mail-domain.example.invalid",
      "password": "Aa123456789012",
      "status": "unused",
      "raw_status": "success",
      "bucket": "unused",
      "error_key": null,
      "error_message": "",
      "copy_count": 2,
      "email_copy_count": 2,
      "password_copy_count": 0
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

## `GET /api/accounts/<id>`

Returns one account.

```json
{
  "account": {
    "id": 301,
    "email": "fake-history@mail-domain.example.invalid",
    "password": "Aa123456789012",
    "status": "unused",
    "raw_status": "success",
    "bucket": "unused",
    "error_key": null,
    "error_message": ""
  }
}
```

## `POST /api/accounts/<id>/copy-email`

Records a successful email-copy action and returns the updated account.

```json
{
  "account": {
    "id": 301,
    "email": "fake-history@mail-domain.example.invalid",
    "email_copy_count": 3
  }
}
```

## `POST /api/accounts/<id>/copy-password`

Records a successful password-copy action and returns the updated account.

```json
{
  "account": {
    "id": 301,
    "password_copy_count": 2,
    "bucket": "used"
  }
}
```

`POST /api/accounts/<id>/copy-account` remains as a compatibility alias for
`copy-email`.

## Error Format

```json
{
  "error": "error.registration.mail_timeout",
  "message": "Registration email did not arrive in time."
}
```

Clients should branch on `error`, not on the localized `message`.
