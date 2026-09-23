"""Tests for the deterministic mock assistant."""

from llm.mock import mock_response


def test_no_actions():
    result = mock_response("How is my portfolio doing?")
    assert result.message == "Mock reply: I can help with your portfolio."
    assert result.trades == [] and result.watchlist_changes == []


def test_buy_and_sell_case_insensitive():
    result = mock_response("BUY 10 aapl and then Sell 2.5 tsla")
    assert [(t.side, t.quantity, t.ticker) for t in result.trades] == [
        ("buy", 10.0, "AAPL"),
        ("sell", 2.5, "TSLA"),
    ]
    assert result.message == "Mock reply: buy 10 AAPL, sell 2.5 TSLA"


def test_watchlist_rules():
    result = mock_response("add PYPL, watch amd, remove NFLX, unwatch V")
    assert [(c.action, c.ticker) for c in result.watchlist_changes] == [
        ("add", "PYPL"),
        ("add", "AMD"),
        ("remove", "NFLX"),
        ("remove", "V"),
    ]


def test_unwatch_is_not_also_watch():
    result = mock_response("unwatch META")
    assert [(c.action, c.ticker) for c in result.watchlist_changes] == [("remove", "META")]


def test_trade_and_watchlist_combined():
    result = mock_response("buy 5 NVDA and add PYPL")
    assert len(result.trades) == 1 and len(result.watchlist_changes) == 1
    assert result.message == "Mock reply: buy 5 NVDA, add PYPL"
