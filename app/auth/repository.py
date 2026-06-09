from dataclasses import dataclass

from app import db as db_module


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    created_at: str
    updated_at: str


class UserRepository:
    def __init__(self, db):
        self.db = db

    def get_by_username(self, username):
        row = self.db.execute(
            "select * from users where username = ?", (username,)
        ).fetchone()
        return _to_user(row)

    def get_by_id(self, user_id):
        row = self.db.execute("select * from users where id = ?", (user_id,)).fetchone()
        return _to_user(row)

    def create(self, username, password_hash):
        now = db_module.utc_now_iso()
        cursor = self.db.execute(
            """
            insert into users (username, password_hash, created_at, updated_at)
            values (?, ?, ?, ?)
            """,
            (username, password_hash, now, now),
        )
        return self.get_by_id(cursor.lastrowid)

    def update_password_hash(self, user_id, password_hash):
        self.db.execute(
            "update users set password_hash = ?, updated_at = ? where id = ?",
            (password_hash, db_module.utc_now_iso(), user_id),
        )


def _to_user(row):
    if row is None:
        return None
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
