"""Background loops: portfolio snapshots and last-price persistence."""

import asyncio
from contextlib import closing

from db import repository as repo
from db.database import get_connection
from market.cache import price_cache
from portfolio.service import record_snapshot_if_changed

SNAPSHOT_SECONDS = 30.0
SAVE_PRICES_SECONDS = 30.0


def save_last_prices() -> None:
    """Persist every cached price so the simulator can resume from it."""
    with closing(get_connection()) as conn, conn:
        repo.save_last_prices(conn, price_cache.prices())


def load_last_prices() -> dict[str, float]:
    """Prices saved by a previous run."""
    with closing(get_connection()) as conn:
        return repo.load_last_prices(conn)


async def snapshot_loop() -> None:
    """Every 30s, record the portfolio value if it changed."""
    while True:
        await asyncio.sleep(SNAPSHOT_SECONDS)
        await asyncio.to_thread(record_snapshot_if_changed)


async def save_prices_loop() -> None:
    """Every 30s, persist the latest prices."""
    while True:
        await asyncio.sleep(SAVE_PRICES_SECONDS)
        await asyncio.to_thread(save_last_prices)
