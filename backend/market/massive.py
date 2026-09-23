"""Massive (formerly Polygon.io) REST client: plan probe, EOD seeds and the snapshot poller."""

import logging
from datetime import date, timedelta
from enum import Enum

import httpx

from market.cache import PriceCache
from market.source import MarketSource

logger = logging.getLogger(__name__)

BASE_URL = "https://api.massive.com"
SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"
GROUPED_PATH = "/v2/aggs/grouped/locale/us/market/stocks/{day}"
POLL_SECONDS = 15.0


class MassivePlan(Enum):
    """What the API key can do, discovered by probing the snapshot endpoint."""

    LIVE = "live"
    EOD_ONLY = "eod_only"
    INVALID = "invalid"


def make_client(api_key: str) -> httpx.AsyncClient:
    """An async HTTP client authenticated against the Massive API."""
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10.0,
    )


def parse_snapshot(ticker_json: dict) -> tuple[str, float, float | None, float | None] | None:
    """Map one snapshot ticker to `(ticker, price, day_open, unix_seconds)`, or None without a price.

    Price falls back from the last trade to the latest minute bar to today's bar.
    `updated` is in nanoseconds.
    """
    day = ticker_json.get("day") or {}
    price = (
        (ticker_json.get("lastTrade") or {}).get("p")
        or (ticker_json.get("min") or {}).get("c")
        or day.get("c")
    )
    if not price:
        return None
    updated = ticker_json.get("updated")
    return ticker_json["ticker"], price, day.get("o") or None, updated / 1e9 if updated else None


async def detect_plan(client: httpx.AsyncClient) -> MassivePlan:
    """Classify the key with one single-ticker snapshot call."""
    response = await client.get(SNAPSHOT_PATH, params={"tickers": "AAPL"})
    if response.status_code == 401:
        return MassivePlan.INVALID
    if response.status_code == 403:
        return MassivePlan.EOD_ONLY
    response.raise_for_status()
    return MassivePlan.LIVE


async def fetch_eod_closes(client: httpx.AsyncClient, tickers: list[str], today: date | None = None) -> dict[str, float]:
    """Latest real closes for the tickers from one grouped-daily call.

    Walks back from yesterday, since weekends and holidays return an empty result.
    """
    day = (today or date.today()) - timedelta(days=1)
    wanted = set(tickers)
    for _ in range(7):
        response = await client.get(GROUPED_PATH.format(day=day.isoformat()), params={"adjusted": "true"})
        response.raise_for_status()
        results = response.json().get("results") or []
        if results:
            return {bar["T"]: bar["c"] for bar in results if bar["T"] in wanted}
        day -= timedelta(days=1)
    return {}


class MassiveSource(MarketSource):
    """Polls the grouped snapshot endpoint for all tracked tickers every 15 seconds."""

    interval = POLL_SECONDS

    def __init__(self, cache: PriceCache, client: httpx.AsyncClient):
        super().__init__(cache)
        self.client = client

    async def tick(self) -> None:
        """One grouped snapshot call; a failed poll keeps the previous prices."""
        tickers = self.cache.tracked()
        if not tickers:
            return
        try:
            response = await self.client.get(SNAPSHOT_PATH, params={"tickers": ",".join(tickers)})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Massive poll failed, keeping previous prices: %s", exc)
            return
        for ticker_json in response.json().get("tickers") or []:
            if parsed := parse_snapshot(ticker_json):
                ticker, price, day_open, timestamp = parsed
                self.cache.update(ticker, price, open_price=day_open, timestamp=timestamp)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
