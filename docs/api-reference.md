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
    "error_key": null,
    "error_message": "",
    "copy_count": 0
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
      "status": "success",
      "error_key": null,
      "error_message": "",
      "copy_count": 2
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
    "status": "success",
    "error_key": null,
    "error_message": ""
  }
}
```

## `POST /api/accounts/<id>/copy-account`

Records a successful email-copy action and returns the updated account.

```json
{
  "account": {
    "id": 301,
    "email": "fake-history@mail-domain.example.invalid",
    "copy_count": 3
  }
}
```

## Error Format

```json
{
  "error": "error.registration.mail_timeout",
  "message": "Registration email did not arrive in time."
}
```

Clients should branch on `error`, not on the localized `message`.
