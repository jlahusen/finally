"""In-memory price cache shared by the market source, SSE stream and services."""

import time
from collections.abc import Callable

from market.models import Direction, PriceUpdate, iso_timestamp


class PriceCache:
    """Latest price per tracked ticker, plus the set of tickers the source should price."""

    def __init__(self) -> None:
        self._updates: dict[str, PriceUpdate] = {}
        self._tracked: set[str] = set()
        self.seeder: Callable[[str], float] | None = None

    def track(self, ticker: str) -> None:
        """Ask the market source to price this ticker; seeds a price now if the source can."""
        ticker = ticker.upper()
        self._tracked.add(ticker)
        if ticker not in self._updates and self.seeder:
            self.update(ticker, self.seeder(ticker))

    def untrack(self, ticker: str) -> None:
        """Stop pricing a ticker and drop its cached price."""
        ticker = ticker.upper()
        self._tracked.discard(ticker)
        self._updates.pop(ticker, None)

    def tracked(self) -> list[str]:
        """Tracked tickers, sorted."""
        return sorted(self._tracked)

    def update(
        self,
        ticker: str,
        price: float,
        open_price: float | None = None,
        timestamp: float | None = None,
    ) -> PriceUpdate:
        """Record a new price; the session open defaults to the first price seen."""
        price = round(price, 2)
        last = self._updates.get(ticker)
        previous = last.price if last else price
        if open_price is None:
            open_price = last.open_price if last else price
        update = PriceUpdate(
            ticker=ticker,
            price=price,
            previous_price=previous,
            open_price=round(open_price, 2),
            direction=_direction(price, previous),
            timestamp=iso_timestamp(timestamp or time.time()),
        )
        self._updates[ticker] = update
        return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Latest update for a ticker, or None before its first price."""
        return self._updates.get(ticker.upper())

    def all(self) -> dict[str, PriceUpdate]:
        """A snapshot copy of every cached update."""
        return dict(self._updates)

    def prices(self) -> dict[str, float]:
        """Latest price per ticker."""
        return {ticker: u.price for ticker, u in self._updates.items()}


def _direction(price: float, previous: float) -> Direction:
    if price > previous:
        return "up"
    if price < previous:
        return "down"
    return "flat"


price_cache = PriceCache()
