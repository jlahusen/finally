"""Correlated geometric Brownian motion price simulator."""

import math

import numpy as np

from market.seeds import profile_for

TICK_SECONDS = 0.5
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
SPEEDUP = 10  # simulated time runs faster so every tick visibly moves
DT = TICK_SECONDS / TRADING_SECONDS_PER_YEAR * SPEEDUP
DRIFT = 0.05
MARKET_WEIGHT = 0.3
SECTOR_WEIGHT = 0.3
EVENT_PROBABILITY = 0.001
EVENT_RANGE = (0.02, 0.05)


class Simulator:
    """Holds a price per ticker and advances all of them one correlated GBM step at a time.

    Each ticker's shock mixes a market-wide factor, a sector factor and its own noise,
    so tickers in the same sector move together.
    """

    def __init__(self, seeds: dict[str, float] | None = None, rng: np.random.Generator | None = None):
        self._seeds = seeds or {}
        self._rng = rng or np.random.default_rng()
        self._prices: dict[str, float] = {}
        self._volatility: dict[str, float] = {}
        self._sector: dict[str, str] = {}

    @property
    def prices(self) -> dict[str, float]:
        """Current price per ticker."""
        return dict(self._prices)

    def seed_price(self, ticker: str) -> float:
        """Starting price: the given seed, else the built-in profile, else a random price."""
        return self._seeds.get(ticker) or profile_for(ticker).price

    def add(self, ticker: str, price: float | None = None) -> float:
        """Start simulating a ticker from `price`, or from its seed price."""
        profile = profile_for(ticker)
        self._prices[ticker] = price or self.seed_price(ticker)
        self._volatility[ticker] = profile.volatility
        self._sector[ticker] = profile.sector
        return self._prices[ticker]

    def remove(self, ticker: str) -> None:
        """Stop simulating a ticker."""
        self._prices.pop(ticker, None)
        self._volatility.pop(ticker, None)
        self._sector.pop(ticker, None)

    def step(self) -> dict[str, float]:
        """Advance every ticker one tick and return the new prices."""
        shocks = self._correlated_shocks()
        for ticker, z in shocks.items():
            sigma = self._volatility[ticker]
            log_return = (DRIFT - sigma**2 / 2) * DT + sigma * math.sqrt(DT) * z
            self._prices[ticker] *= math.exp(log_return) * self._event_factor()
        return self.prices

    def _correlated_shocks(self) -> dict[str, float]:
        market = self._rng.standard_normal()
        sectors = {s: self._rng.standard_normal() for s in set(self._sector.values())}
        own_weight = math.sqrt(1 - MARKET_WEIGHT - SECTOR_WEIGHT)
        return {
            ticker: math.sqrt(MARKET_WEIGHT) * market
            + math.sqrt(SECTOR_WEIGHT) * sectors[sector]
            + own_weight * self._rng.standard_normal()
            for ticker, sector in self._sector.items()
        }

    def _event_factor(self) -> float:
        """Usually 1; rarely a sudden 2-5% jump up or down."""
        if self._rng.random() >= EVENT_PROBABILITY:
            return 1.0
        move = self._rng.uniform(*EVENT_RANGE)
        return 1 + move if self._rng.random() < 0.5 else 1 - move
