"""Built-in seed prices and per-ticker simulation parameters."""

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TickerProfile:
    """Starting price, annualised volatility and sector used for correlation."""

    price: float
    volatility: float
    sector: str


PROFILES: dict[str, TickerProfile] = {
    "AAPL": TickerProfile(190.0, 0.25, "tech"),
    "GOOGL": TickerProfile(175.0, 0.28, "tech"),
    "MSFT": TickerProfile(420.0, 0.24, "tech"),
    "AMZN": TickerProfile(185.0, 0.30, "tech"),
    "TSLA": TickerProfile(250.0, 0.55, "tech"),
    "NVDA": TickerProfile(880.0, 0.50, "tech"),
    "META": TickerProfile(500.0, 0.35, "tech"),
    "JPM": TickerProfile(200.0, 0.20, "finance"),
    "V": TickerProfile(280.0, 0.18, "finance"),
    "NFLX": TickerProfile(620.0, 0.40, "tech"),
}

DEFAULT_VOLATILITY = 0.35


def profile_for(ticker: str) -> TickerProfile:
    """The built-in profile, or a generated one with a plausible random price."""
    return PROFILES.get(ticker) or TickerProfile(
        round(random.uniform(20, 400), 2), DEFAULT_VOLATILITY, "other"
    )
