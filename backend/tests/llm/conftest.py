"""Fixtures for chat tests: fake portfolio and watchlist services."""

import pytest

from llm import service
from portfolio.service import TradeError


class FakeServices:
    """Records calls and simulates cash/share checks and watchlist membership."""

    def __init__(self):
        self.cash = 1000.0
        self.held = {"AAPL": 4.0}
        self.watchlist = {"AAPL", "NFLX"}
        self.prices = {"AAPL": 191.24, "NVDA": 100.0}
        self.trades = []

    def execute_trade(self, ticker, side, quantity):
        price = self.prices[ticker]
        if side == "buy" and quantity * price > self.cash:
            raise TradeError(f"insufficient cash (${quantity * price:,.2f} needed, ${self.cash:,.2f} available)")
        if side == "sell" and quantity > self.held.get(ticker, 0):
            raise TradeError(f"insufficient shares ({quantity:g} requested, {self.held.get(ticker, 0):g} held)")
        self.trades.append((ticker, side, quantity))
        return {"ticker": ticker, "side": side, "quantity": quantity, "price": price}

    def add(self, ticker):
        added = ticker not in self.watchlist
        self.watchlist.add(ticker)
        return added

    def remove(self, ticker):
        present = ticker in self.watchlist
        self.watchlist.discard(ticker)
        return present

    def get_portfolio(self):
        return {"cash": self.cash, "total_value": self.cash, "unrealized_pnl": 0.0, "positions": []}

    def list_items(self):
        return [{"ticker": t, "price": self.prices.get(t)} for t in sorted(self.watchlist)]


@pytest.fixture
def fake(monkeypatch):
    """Patch the portfolio/watchlist functions used by `llm` with a `FakeServices` instance."""
    services = FakeServices()
    portfolio, watchlist = service.portfolio_service, service.watchlist_service
    monkeypatch.setattr(portfolio, "execute_trade", services.execute_trade)
    monkeypatch.setattr(portfolio, "get_portfolio", services.get_portfolio)
    monkeypatch.setattr(watchlist, "add", services.add)
    monkeypatch.setattr(watchlist, "remove", services.remove)
    monkeypatch.setattr(watchlist, "list_items", services.list_items)
    return services
