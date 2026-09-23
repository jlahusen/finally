"""All SQL for FinAlly. Plain functions taking `conn` first; callers own transactions."""

import json
import sqlite3

from db.database import new_id, now_iso


def _qty(value: float) -> float:
    return round(value, 4)


def _money(value: float) -> float:
    return round(value, 2)


# --- cash ---

def get_cash(conn: sqlite3.Connection, user_id: str = "default") -> float:
    """Current cash balance."""
    return conn.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()[0]


def set_cash(conn: sqlite3.Connection, cash: float, user_id: str = "default") -> None:
    """Set the cash balance, rounded to cents."""
    conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (_money(cash), user_id))


# --- watchlist ---

def list_watchlist(conn: sqlite3.Connection, user_id: str = "default") -> list[str]:
    """Watchlist tickers in the order they were added."""
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid", (user_id,)
    )
    return [row["ticker"] for row in rows]


def add_watchlist(conn: sqlite3.Connection, ticker: str, user_id: str = "default") -> bool:
    """Add a ticker; False if it was already present."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (new_id(), user_id, ticker.upper(), now_iso()),
    )
    return cur.rowcount == 1


def remove_watchlist(conn: sqlite3.Connection, ticker: str, user_id: str = "default") -> bool:
    """Remove a ticker; False if it was absent."""
    cur = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper())
    )
    return cur.rowcount == 1


# --- positions ---

def list_positions(conn: sqlite3.Connection, user_id: str = "default") -> list[dict]:
    """All open positions as dicts with `ticker, quantity, avg_cost`, sorted by ticker."""
    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    )
    return [dict(row) for row in rows]


def get_position(conn: sqlite3.Connection, ticker: str, user_id: str = "default") -> dict | None:
    """One position, or None if not held."""
    row = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker.upper()),
    ).fetchone()
    return dict(row) if row else None


def save_position(
    conn: sqlite3.Connection, ticker: str, quantity: float, avg_cost: float, user_id: str = "default"
) -> None:
    """Upsert a position; deletes the row when the rounded quantity is zero."""
    ticker, quantity = ticker.upper(), _qty(quantity)
    if quantity == 0:
        conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))
        return
    conn.execute(
        """INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (user_id, ticker) DO UPDATE SET
             quantity = excluded.quantity, avg_cost = excluded.avg_cost, updated_at = excluded.updated_at""",
        (new_id(), user_id, ticker, quantity, _money(avg_cost), now_iso()),
    )


# --- trades ---

def insert_trade(
    conn: sqlite3.Connection, ticker: str, side: str, quantity: float, price: float, user_id: str = "default"
) -> dict:
    """Append a trade to the log and return it."""
    trade = {
        "id": new_id(),
        "ticker": ticker.upper(),
        "side": side,
        "quantity": _qty(quantity),
        "price": _money(price),
        "executed_at": now_iso(),
    }
    conn.execute(
        """INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
           VALUES (:id, :user_id, :ticker, :side, :quantity, :price, :executed_at)""",
        {**trade, "user_id": user_id},
    )
    return trade


def list_trades(conn: sqlite3.Connection, limit: int = 50, user_id: str = "default") -> list[dict]:
    """Most recent trades, newest first."""
    rows = conn.execute(
        """SELECT id, ticker, side, quantity, price, executed_at FROM trades
           WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?""",
        (user_id, limit),
    )
    return [dict(row) for row in rows]


# --- portfolio snapshots ---

def insert_snapshot(conn: sqlite3.Connection, total_value: float, user_id: str = "default") -> None:
    """Record the portfolio's total value now."""
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (new_id(), user_id, _money(total_value), now_iso()),
    )


def last_snapshot_value(conn: sqlite3.Connection, user_id: str = "default") -> float | None:
    """Total value of the most recent snapshot, or None if there are none."""
    row = conn.execute(
        """SELECT total_value FROM portfolio_snapshots WHERE user_id = ?
           ORDER BY recorded_at DESC, rowid DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    return row[0] if row else None


def list_snapshots(conn: sqlite3.Connection, limit: int = 200, user_id: str = "default") -> list[dict]:
    """Snapshots oldest first, evenly downsampled to at most `limit`, always keeping the latest."""
    rows = conn.execute(
        """SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id = ?
           ORDER BY recorded_at, rowid""",
        (user_id,),
    ).fetchall()
    return [dict(rows[i]) for i in _sample_indices(len(rows), limit)]


def _sample_indices(count: int, limit: int) -> list[int]:
    """Evenly spaced indices into `count` items, at most `limit`, including the last."""
    if count <= limit:
        return list(range(count))
    if limit == 1:
        return [count - 1]
    return [round(i * (count - 1) / (limit - 1)) for i in range(limit)]


# --- last prices ---

def load_last_prices(conn: sqlite3.Connection) -> dict[str, float]:
    """Last known price per ticker."""
    return {row["ticker"]: row["price"] for row in conn.execute("SELECT ticker, price FROM last_prices")}


def save_last_prices(conn: sqlite3.Connection, prices: dict[str, float]) -> None:
    """Upsert the latest price for each ticker."""
    now = now_iso()
    conn.executemany(
        """INSERT INTO last_prices (ticker, price, updated_at) VALUES (?, ?, ?)
           ON CONFLICT (ticker) DO UPDATE SET price = excluded.price, updated_at = excluded.updated_at""",
        [(ticker.upper(), _money(price), now) for ticker, price in prices.items()],
    )


# --- chat ---

def insert_chat_message(
    conn: sqlite3.Connection, role: str, content: str, actions: list | None, user_id: str = "default"
) -> dict:
    """Store a chat message (actions as JSON) and return it with `actions` as a list or None."""
    message = {"id": new_id(), "role": role, "content": content, "actions": actions, "created_at": now_iso()}
    conn.execute(
        """INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (message["id"], user_id, role, content, _dump(actions), message["created_at"]),
    )
    return message


def list_chat_messages(conn: sqlite3.Connection, limit: int = 50, user_id: str = "default") -> list[dict]:
    """The latest `limit` chat messages, returned oldest first."""
    rows = conn.execute(
        """SELECT id, role, content, actions, created_at FROM chat_messages WHERE user_id = ?
           ORDER BY created_at DESC, rowid DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [{**dict(row), "actions": _load(row["actions"])} for row in reversed(rows)]


def _dump(actions: list | None) -> str | None:
    return None if actions is None else json.dumps(actions)


def _load(actions: str | None) -> list | None:
    return None if actions is None else json.loads(actions)
