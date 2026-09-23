"""Pick the market data source from the environment and the Massive key's plan."""

import logging
import os

import httpx

from market.cache import PriceCache
from market.massive import MassivePlan, MassiveSource, detect_plan, fetch_eod_closes, make_client
from market.source import MarketSource, SimulatorSource

logger = logging.getLogger(__name__)


async def create_source(cache: PriceCache, last_prices: dict[str, float], tickers: list[str]) -> MarketSource:
    """Massive poller for a live key, otherwise the simulator; `tickers` are those tracked at startup.

    Simulator seed precedence: `last_prices` -> Massive EOD close -> built-in -> random.
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if not api_key:
        logger.info("Market data: simulator (no MASSIVE_API_KEY)")
        return SimulatorSource(cache, last_prices)
    client = make_client(api_key)
    return await _source_for_key(cache, last_prices, tickers, client)


async def _source_for_key(
    cache: PriceCache, last_prices: dict[str, float], tickers: list[str], client: httpx.AsyncClient
) -> MarketSource:
    try:
        plan = await detect_plan(client)
    except httpx.HTTPError as exc:
        logger.warning("Market data: Massive unreachable (%r); using the simulator", exc)
        plan = None
    if plan is MassivePlan.LIVE:
        logger.info("Market data: Massive live snapshots every 15s")
        return MassiveSource(cache, client)
    try:
        if plan is MassivePlan.INVALID:
            logger.warning("Market data: MASSIVE_API_KEY rejected (401); using the simulator")
        if plan in (None, MassivePlan.INVALID):
            return SimulatorSource(cache, last_prices)
        closes = await fetch_eod_closes(client, tickers)
        logger.info("Market data: Massive free tier; simulating from %d real EOD closes", len(closes))
        return SimulatorSource(cache, {**closes, **last_prices})
    finally:
        await client.aclose()
