from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AccountStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class Account:
    id: int
    email: str
    password: str
    status: str
    error_message: str | None
    copy_count: int
    last_copied_at: str | None
    created_by: int | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Page:
    items: list[Account]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class CopyResult:
    account: Account


@dataclass(frozen=True)
class RegistrationResult:
    account: Account


@dataclass(frozen=True)
class RegistrationProfile:
    password: str
    name_sei: str
    name_mei: str
    kana_sei: str
    kana_mei: str
    phone_a: str
    phone_e: str
    phone_n: str
