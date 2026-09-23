"""Tests for portfolio context and message construction."""

from llm.prompt import SYSTEM_PROMPT, build_context, build_messages

PORTFOLIO = {
    "cash": 8087.60,
    "total_value": 10020.00,
    "unrealized_pnl": 107.60,
    "positions": [
        {
            "ticker": "AAPL",
            "quantity": 10,
            "avg_cost": 191.24,
            "current_price": 200.00,
            "market_value": 2000.00,
            "unrealized_pnl": 87.60,
            "pnl_pct": 4.58,
        }
    ],
}
WATCHLIST = [{"ticker": "AAPL", "price": 200.0}, {"ticker": "PYPL", "price": None}]


def test_context_includes_portfolio_and_watchlist():
    context = build_context(PORTFOLIO, WATCHLIST)
    assert "Cash: $8,087.60" in context
    assert "Total portfolio value: $10,020.00" in context
    assert "AAPL: 10 shares, avg cost $191.24" in context
    assert "(4.58%)" in context
    assert "- PYPL: n/a" in context


def test_context_empty_portfolio():
    context = build_context({**PORTFOLIO, "positions": []}, [])
    assert "Positions:\n- none" in context
    assert "Watchlist:\n- empty" in context


def test_build_messages_order_and_action_outcomes():
    history = [
        {"role": "user", "content": "buy 10 AAPL", "actions": None},
        {"role": "assistant", "content": "On it", "actions": [{"text": "✓ Bought 10 AAPL @ $191.24"}]},
    ]
    messages = build_messages("ctx", history, "thanks")
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["content"].endswith("ctx")
    assert messages[2] == {"role": "user", "content": "buy 10 AAPL"}
    assert messages[3] == {"role": "assistant", "content": "On it\n✓ Bought 10 AAPL @ $191.24"}
    assert messages[4] == {"role": "user", "content": "thanks"}
