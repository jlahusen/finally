"""Trade execution and portfolio valuation against live cache prices."""

import sqlite3
from contextlib import closing

from db import repository as repo
from db.database import get_connection
from market.cache import price_cache

CASH_TOLERANCE = 0.01


class TradeError(Exception):
    """A trade rejected by validation; the message is shown to the user verbatim."""


def execute_trade(ticker: str, side: str, quantity: float) -> dict:
    """Validate and execute a market order at the cached price; returns the trade dict.

    Cash, position, trade log and a portfolio snapshot are written in one transaction.
    A buy also adds the ticker to the watchlist.
    """
    ticker, quantity = ticker.upper(), round(quantity, 4)
    if quantity <= 0:
        raise TradeError("quantity must be positive")
    if price_cache.get(ticker) is None:
        price_cache.track(ticker)
    update = price_cache.get(ticker)
    if update is None:
        raise TradeError(f"no price available for {ticker}")
    with closing(get_connection()) as conn, conn:
        if side == "buy":
            _buy(conn, ticker, quantity, update.price)
            repo.add_watchlist(conn, ticker)
        else:
            _sell(conn, ticker, quantity, update.price)
        trade = repo.insert_trade(conn, ticker, side, quantity, update.price)
        repo.insert_snapshot(conn, _total_value(conn))
    price_cache.track(ticker)
    return trade


def _buy(conn: sqlite3.Connection, ticker: str, quantity: float, price: float) -> None:
    cash, cost = repo.get_cash(conn), round(quantity * price, 2)
    if cost > cash + CASH_TOLERANCE:
        raise TradeError(f"insufficient cash ({_money(cost)} needed, {_money(cash)} available)")
    held = repo.get_position(conn, ticker) or {"quantity": 0.0, "avg_cost": 0.0}
    new_quantity = held["quantity"] + quantity
    avg_cost = (held["quantity"] * held["avg_cost"] + quantity * price) / new_quantity
    repo.set_cash(conn, max(cash - cost, 0.0))
    repo.save_position(conn, ticker, new_quantity, avg_cost)


def _sell(conn: sqlite3.Connection, ticker: str, quantity: float, price: float) -> None:
    held = repo.get_position(conn, ticker)
    held_quantity = held["quantity"] if held else 0.0
    if quantity > held_quantity:
        raise TradeError(f"insufficient shares ({_qty(quantity)} requested, {_qty(held_quantity)} held)")
    repo.set_cash(conn, repo.get_cash(conn) + quantity * price)
    repo.save_position(conn, ticker, held_quantity - quantity, held["avg_cost"])


def get_portfolio() -> dict:
    """Cash, positions valued at live prices, total value and unrealized P&L."""
    with closing(get_connection()) as conn:
        cash = repo.get_cash(conn)
        positions = [_valued(p) for p in repo.list_positions(conn)]
    return {
        "cash": cash,
        "total_value": round(cash + sum((p["market_value"] for p in positions), 0.0), 2),
        "unrealized_pnl": round(sum((p["unrealized_pnl"] for p in positions), 0.0), 2),
        "positions": positions,
    }


def history(limit: int = 200) -> list[dict]:
    """Portfolio value snapshots, oldest first, downsampled to at most `limit`."""
    with closing(get_connection()) as conn:
        return repo.list_snapshots(conn, limit)


def trades(limit: int = 50) -> list[dict]:
    """Trade log, newest first."""
    with closing(get_connection()) as conn:
        return repo.list_trades(conn, limit)


def record_snapshot_if_changed() -> bool:
    """Write a portfolio snapshot unless the total value equals the last one."""
    with closing(get_connection()) as conn, conn:
        total = round(_total_value(conn), 2)
        if total == repo.last_snapshot_value(conn):
            return False
        repo.insert_snapshot(conn, total)
        return True


def _valued(position: dict) -> dict:
    """A position with current price (avg cost until the first tick), value and P&L."""
    update = price_cache.get(position["ticker"])
    price = update.price if update else position["avg_cost"]
    cost = position["avg_cost"]
    return {
        **position,
        "current_price": price,
        "market_value": round(position["quantity"] * price, 2),
        "unrealized_pnl": round(position["quantity"] * (price - cost), 2),
        "pnl_pct": round((price / cost - 1) * 100, 2) if cost else 0.0,
    }


def _total_value(conn: sqlite3.Connection) -> float:
    return repo.get_cash(conn) + sum(_valued(p)["market_value"] for p in repo.list_positions(conn))


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _qty(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")
