"""Watchlist add/remove/list, keeping the price cache's tracked set in step."""

from contextlib import closing

from db import repository as repo
from db.database import get_connection
from market.cache import price_cache

PRICE_FIELDS = ("price", "previous_price", "open_price", "direction", "timestamp")


def add(ticker: str) -> bool:
    """Add a ticker and start pricing it; False if already present."""
    ticker = ticker.upper()
    with closing(get_connection()) as conn, conn:
        added = repo.add_watchlist(conn, ticker)
    price_cache.track(ticker)
    return added


def remove(ticker: str) -> bool:
    """Remove a ticker; keeps pricing it while a position is open. False if absent."""
    ticker = ticker.upper()
    with closing(get_connection()) as conn, conn:
        removed = repo.remove_watchlist(conn, ticker)
        held = repo.get_position(conn, ticker) is not None
    if removed and not held:
        price_cache.untrack(ticker)
    return removed


def item(ticker: str) -> dict:
    """A watchlist row: the ticker with its latest price fields, null before the first tick."""
    update = price_cache.get(ticker)
    prices = update.to_dict() if update else dict.fromkeys(PRICE_FIELDS)
    return {**prices, "ticker": ticker}


def list_items() -> list[dict]:
    """Every watchlist ticker in added order, with latest prices."""
    with closing(get_connection()) as conn:
        tickers = repo.list_watchlist(conn)
    return [item(t) for t in tickers]


def tracked_tickers() -> set[str]:
    """Watchlist tickers plus tickers with an open position."""
    with closing(get_connection()) as conn:
        return set(repo.list_watchlist(conn)) | {p["ticker"] for p in repo.list_positions(conn)}
