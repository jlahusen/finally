"""Trade execution, validation, valuation, snapshots and the watchlist service."""

import pytest

from db import repository as repo
from market.cache import price_cache
from market.source import SimulatorSource
from portfolio.service import TradeError, execute_trade, get_portfolio, record_snapshot_if_changed
from watchlist import service as watchlist


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    """Fresh cache prices for each test, with no source seeding new tickers."""
    monkeypatch.setattr(price_cache, "seeder", None)
    for ticker in set(price_cache.all()) | set(price_cache.tracked()):
        price_cache.untrack(ticker)
    price_cache.update("AAPL", 100.0)
    price_cache.update("PYPL", 50.0)


def test_buy_updates_cash_position_trade_snapshot_and_watchlist(conn):
    trade = execute_trade("pypl", "buy", 10)
    assert (trade["ticker"], trade["side"], trade["quantity"], trade["price"]) == ("PYPL", "buy", 10, 50.0)
    assert repo.get_cash(conn) == 9500.0
    assert repo.get_position(conn, "PYPL") == {"ticker": "PYPL", "quantity": 10, "avg_cost": 50.0}
    assert repo.last_snapshot_value(conn) == 10000.0
    assert "PYPL" in repo.list_watchlist(conn)
    assert "PYPL" in price_cache.tracked()


def test_average_cost_across_buys(conn):
    execute_trade("AAPL", "buy", 10)
    price_cache.update("AAPL", 120.0)
    execute_trade("AAPL", "buy", 10)
    assert repo.get_position(conn, "AAPL")["avg_cost"] == 110.0


def test_insufficient_cash_message():
    with pytest.raises(TradeError, match=r"^insufficient cash \(\$10,100\.00 needed, \$10,000\.00 available\)$"):
        execute_trade("AAPL", "buy", 101)


def test_cent_tolerance_allows_exact_fit(conn):
    price_cache.update("AAPL", 1000.001)  # cached as 1000.0
    repo.set_cash(conn, 9999.99)
    conn.commit()
    execute_trade("AAPL", "buy", 10)
    assert repo.get_cash(conn) == 0.0


def test_sell_more_than_held():
    execute_trade("AAPL", "buy", 4)
    with pytest.raises(TradeError, match=r"^insufficient shares \(10 requested, 4 held\)$"):
        execute_trade("AAPL", "sell", 10)


def test_sell_at_loss_and_full_sell_removes_row(conn):
    execute_trade("AAPL", "buy", 10)
    price_cache.update("AAPL", 90.0)
    execute_trade("AAPL", "sell", 4)
    assert repo.get_position(conn, "AAPL")["quantity"] == 6
    assert repo.get_cash(conn) == 9000.0 + 360.0
    execute_trade("AAPL", "sell", 6)
    assert repo.get_position(conn, "AAPL") is None
    assert repo.get_cash(conn) == 9900.0


def test_fractional_quantities(conn):
    execute_trade("AAPL", "buy", 0.5)
    execute_trade("AAPL", "sell", 0.25)
    assert repo.get_position(conn, "AAPL")["quantity"] == 0.25


def test_invalid_quantity_and_unknown_price():
    with pytest.raises(TradeError, match="^quantity must be positive$"):
        execute_trade("AAPL", "buy", 0)
    with pytest.raises(TradeError, match="^no price available for XYZ$"):
        execute_trade("xyz", "buy", 1)


def test_get_portfolio_valuation():
    execute_trade("AAPL", "buy", 10)
    price_cache.update("AAPL", 110.0)
    portfolio = get_portfolio()
    assert portfolio["cash"] == 9000.0
    assert portfolio["total_value"] == 10100.0
    assert portfolio["unrealized_pnl"] == 100.0
    assert portfolio["positions"] == [
        {"ticker": "AAPL", "quantity": 10, "avg_cost": 100.0, "current_price": 110.0,
         "market_value": 1100.0, "unrealized_pnl": 100.0, "pnl_pct": 10.0}
    ]


def test_snapshot_skips_unchanged_value():
    assert record_snapshot_if_changed() is True
    assert record_snapshot_if_changed() is False


def test_watchlist_add_remove_and_tracking():
    assert watchlist.add("pypl") is True
    assert watchlist.add("PYPL") is False
    assert watchlist.list_items()[-1] == {"ticker": "PYPL", **price_cache.get("PYPL").to_dict()}
    assert watchlist.remove("PYPL") is True
    assert watchlist.remove("PYPL") is False
    assert "PYPL" not in price_cache.tracked()


def test_remove_keeps_tracking_open_position():
    execute_trade("AAPL", "buy", 1)
    watchlist.remove("AAPL")
    assert "AAPL" in price_cache.tracked()
    assert "AAPL" in watchlist.tracked_tickers()


def test_list_items_nulls_before_first_tick():
    watchlist.add("NEWT")
    assert watchlist.list_items()[-1] == {
        "ticker": "NEWT", "price": None, "previous_price": None,
        "open_price": None, "direction": None, "timestamp": None,
    }


def test_buy_untracked_ticker_prices_it_immediately(conn):
    SimulatorSource(price_cache)
    assert price_cache.get("ZZZZ") is None
    trade = execute_trade("ZZZZ", "buy", 1)
    assert trade["price"] == price_cache.get("ZZZZ").price > 0
    assert "ZZZZ" in repo.list_watchlist(conn)
