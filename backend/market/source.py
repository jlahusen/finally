"""The market data source interface and the simulator-backed implementation."""

import asyncio
from abc import ABC, abstractmethod

from market.cache import PriceCache
from market.simulator import TICK_SECONDS, Simulator


class MarketSource(ABC):
    """Writes prices for the cache's tracked tickers into the cache until cancelled."""

    def __init__(self, cache: PriceCache):
        self.cache = cache
        cache.seeder = None

    @abstractmethod
    async def tick(self) -> None:
        """Refresh prices for every tracked ticker once."""

    @property
    @abstractmethod
    def interval(self) -> float:
        """Seconds between ticks."""

    async def run(self) -> None:
        """Tick forever; cancel the task to stop."""
        while True:
            await self.tick()
            await asyncio.sleep(self.interval)

    async def close(self) -> None:
        """Release any resources held by the source."""


class SimulatorSource(MarketSource):
    """Prices tracked tickers with the GBM simulator every half second."""

    interval = TICK_SECONDS

    def __init__(self, cache: PriceCache, seeds: dict[str, float] | None = None, simulator: Simulator | None = None):
        super().__init__(cache)
        self.simulator = simulator or Simulator(seeds)
        cache.seeder = self.simulator.seed_price

    async def tick(self) -> None:
        """Sync the simulated set with the tracked set, step, and write the cache.

        A newly tracked ticker continues from the price the cache was seeded with.
        """
        tracked = set(self.cache.tracked())
        simulated = set(self.simulator.prices)
        for ticker in simulated - tracked:
            self.simulator.remove(ticker)
        for ticker in tracked - simulated:
            seeded = self.cache.get(ticker)
            self.cache.update(ticker, self.simulator.add(ticker, seeded and seeded.price))
        for ticker, price in self.simulator.step().items():
            self.cache.update(ticker, price)
