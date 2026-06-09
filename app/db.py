import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = get_db()
        db.execute("pragma journal_mode = wal")
        run_migrations(db)


def connect_db(sqlite_path):
    if sqlite_path != ":memory:":
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(sqlite_path, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("pragma foreign_keys = on")
    db.execute("pragma busy_timeout = 30000")
    return db


def get_db():
    if "db" not in g:
        config = current_app.config["APP_CONFIG"]
        g.db = connect_db(config.sqlite_path)
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transaction():
    db = get_db()
    try:
        db.execute("begin")
        yield db
        db.execute("commit")
    except Exception:
        db.execute("rollback")
        raise


def run_migrations(db):
    db.execute(
        """
        create table if not exists schema_migrations (
          version text primary key,
          applied_at text not null
        )
        """
    )
    migrations_dir = Path(current_app.root_path).parent / "migrations"
    for path in sorted(migrations_dir.glob("*.sql")):
        version = path.stem
        row = db.execute(
            "select version from schema_migrations where version = ?", (version,)
        ).fetchone()
        if row:
            continue
        with path.open("r", encoding="utf-8") as migration:
            sql = migration.read()
        db.executescript(sql)
        db.execute(
            "insert into schema_migrations (version, applied_at) values (?, ?)",
            (version, utc_now_iso()),
        )


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
