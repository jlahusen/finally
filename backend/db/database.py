"""SQLite connection handling, lazy schema creation and default seed data."""

import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "db" / "finally.db"
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
DEFAULT_CASH = 10000.0

_initialized: set[Path] = set()


def now_iso() -> str:
    """Current UTC time as ISO 8601 with millisecond precision and a `Z` suffix."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id() -> str:
    """A fresh UUID4 string for primary keys."""
    return str(uuid.uuid4())


def db_path() -> Path:
    """Database file path: `FINALLY_DB_PATH` if set, else `<project root>/db/finally.db`."""
    return Path(os.environ.get("FINALLY_DB_PATH") or DEFAULT_DB_PATH)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db(path: Path | None = None) -> None:
    """Create the schema if missing, enable WAL and seed default data on a fresh database."""
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_PATH.read_text())
        with conn:
            _seed(conn)
    finally:
        conn.close()
    _initialized.add(path)


def _seed(conn: sqlite3.Connection) -> None:
    """Insert the default user and watchlist, only when the user profile does not exist yet."""
    if conn.execute("SELECT 1 FROM users_profile WHERE id = 'default'").fetchone():
        return
    now = now_iso()
    conn.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES ('default', ?, ?)",
        (DEFAULT_CASH, now),
    )
    conn.executemany(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
        [(new_id(), ticker, now) for ticker in DEFAULT_TICKERS],
    )


def get_connection() -> sqlite3.Connection:
    """Open a new connection, initializing the database on first use in this process."""
    path = db_path()
    if path not in _initialized:
        init_db(path)
    return _connect(path)
