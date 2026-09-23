"""Tests for repository functions against a temp database."""

from db import repository as repo
from db.database import DEFAULT_TICKERS


def test_cash_get_and_set_rounds(conn):
    assert repo.get_cash(conn) == 10000.0
    repo.set_cash(conn, 1234.5678)
    assert repo.get_cash(conn) == 1234.57


def test_watchlist_add_remove(conn):
    assert repo.list_watchlist(conn) == DEFAULT_TICKERS
    assert repo.add_watchlist(conn, "pypl") is True
    assert repo.add_watchlist(conn, "PYPL") is False
    assert repo.list_watchlist(conn)[-1] == "PYPL"
    assert repo.remove_watchlist(conn, "pypl") is True
    assert repo.remove_watchlist(conn, "PYPL") is False
    assert "PYPL" not in repo.list_watchlist(conn)


def test_position_upsert_and_rounding(conn):
    assert repo.get_position(conn, "AAPL") is None
    repo.save_position(conn, "aapl", 1.23456, 190.123)
    assert repo.get_position(conn, "AAPL") == {"ticker": "AAPL", "quantity": 1.2346, "avg_cost": 190.12}
    repo.save_position(conn, "AAPL", 3, 200)
    assert repo.list_positions(conn) == [{"ticker": "AAPL", "quantity": 3.0, "avg_cost": 200.0}]


def test_position_deleted_at_zero_quantity(conn):
    repo.save_position(conn, "AAPL", 2, 190)
    repo.save_position(conn, "AAPL", 0.00001, 190)
    assert repo.get_position(conn, "AAPL") is None
    assert repo.list_positions(conn) == []


def test_trades_insert_and_list_newest_first(conn):
    first = repo.insert_trade(conn, "aapl", "buy", 1.00004, 190.126)
    assert first["ticker"] == "AAPL" and first["quantity"] == 1.0 and first["price"] == 190.13
    assert first["executed_at"].endswith("Z")
    second = repo.insert_trade(conn, "MSFT", "sell", 2, 400)
    trades = repo.list_trades(conn)
    assert [t["id"] for t in trades] == [second["id"], first["id"]]
    assert trades[1] == first
    assert len(repo.list_trades(conn, limit=1)) == 1


def test_snapshots_last_value(conn):
    assert repo.last_snapshot_value(conn) is None
    repo.insert_snapshot(conn, 10000.004)
    repo.insert_snapshot(conn, 10500.5)
    assert repo.last_snapshot_value(conn) == 10500.5


def test_snapshots_downsampled_keep_latest(conn):
    for value in range(1000):
        repo.insert_snapshot(conn, value)
    snaps = repo.list_snapshots(conn, limit=200)
    values = [s["total_value"] for s in snaps]
    assert len(values) == 200
    assert values[0] == 0 and values[-1] == 999
    assert values == sorted(values)
    assert set(snaps[0]) == {"total_value", "recorded_at"}


def test_snapshots_small_and_limit_one(conn):
    for value in (1, 2, 3):
        repo.insert_snapshot(conn, value)
    assert [s["total_value"] for s in repo.list_snapshots(conn)] == [1, 2, 3]
    assert [s["total_value"] for s in repo.list_snapshots(conn, limit=1)] == [3]


def test_last_prices_roundtrip(conn):
    assert repo.load_last_prices(conn) == {}
    repo.save_last_prices(conn, {"aapl": 190.123, "MSFT": 400})
    repo.save_last_prices(conn, {"AAPL": 191})
    assert repo.load_last_prices(conn) == {"AAPL": 191.0, "MSFT": 400.0}


def test_chat_messages_actions_json_and_order(conn):
    actions = [{"type": "trade", "ticker": "AAPL", "ok": True, "text": "✓ Bought 10 AAPL @ $191.24"}]
    user = repo.insert_chat_message(conn, "user", "buy 10 AAPL", None)
    reply = repo.insert_chat_message(conn, "assistant", "Done", actions)
    assert reply["actions"] == actions and reply["created_at"].endswith("Z")
    messages = repo.list_chat_messages(conn)
    assert messages == [user, reply]


def test_chat_messages_latest_limit_oldest_first(conn):
    for i in range(5):
        repo.insert_chat_message(conn, "user", f"m{i}", None)
    assert [m["content"] for m in repo.list_chat_messages(conn, limit=3)] == ["m2", "m3", "m4"]
