"""Deterministic mock assistant for `LLM_MOCK=true` (E2E tests, development without a key)."""

import re

from llm.schema import LLMResponse, TradeRequest, WatchlistChange

TICKER = r"([A-Za-z][A-Za-z0-9.\-]{0,9})\b"
TRADE_PATTERN = re.compile(rf"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+{TICKER}", re.IGNORECASE)
WATCH_PATTERN = re.compile(rf"\b(add|watch|remove|unwatch)\s+{TICKER}", re.IGNORECASE)
WATCH_ACTIONS = {"add": "add", "watch": "add", "remove": "remove", "unwatch": "remove"}


def format_quantity(quantity: float) -> str:
    """Render a quantity without trailing zeros, e.g. 10.0 -> '10', 0.5 -> '0.5'."""
    return f"{quantity:.4f}".rstrip("0").rstrip(".")


def mock_response(user_message: str) -> LLMResponse:
    """Build a reply from `buy/sell <qty> <TICKER>` and `add/watch/remove/unwatch <TICKER>` rules."""
    trades = [
        TradeRequest(side=side.lower(), quantity=float(qty), ticker=ticker.upper())
        for side, qty, ticker in TRADE_PATTERN.findall(user_message)
    ]
    changes = [
        WatchlistChange(action=WATCH_ACTIONS[verb.lower()], ticker=ticker.upper())
        for verb, ticker in WATCH_PATTERN.findall(user_message)
    ]
    parts = [f"{t.side} {format_quantity(t.quantity)} {t.ticker}" for t in trades]
    parts += [f"{c.action} {c.ticker}" for c in changes]
    summary = ", ".join(parts) if parts else "I can help with your portfolio."
    return LLMResponse(message=f"Mock reply: {summary}", trades=trades, watchlist_changes=changes)
