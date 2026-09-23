"""Tests for connection handling, lazy init and seed data."""

from db.database import DEFAULT_TICKERS, db_path, get_connection, init_db, now_iso


def test_db_path_uses_env(temp_db):
    assert db_path() == temp_db


def test_get_connection_creates_and_seeds(temp_db):
    conn = get_connection()
    assert temp_db.exists()
    assert conn.execute("SELECT cash_balance FROM users_profile").fetchone()[0] == 10000.0
    tickers = [r["ticker"] for r in conn.execute("SELECT ticker FROM watchlist ORDER BY rowid")]
    assert tickers == DEFAULT_TICKERS
    conn.close()


def test_wal_mode_enabled(conn):
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_init_is_idempotent_and_does_not_reseed(temp_db, conn):
    with conn:
        conn.execute("DELETE FROM watchlist")
    init_db(temp_db)
    assert conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1


def test_now_iso_format():
    ts = now_iso()
    assert ts.endswith("Z") and "T" in ts and len(ts) == 24
