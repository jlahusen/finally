"""SSE endpoint pushing one array of changed prices per tick."""

import asyncio
import time
from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from market.cache import PriceCache, price_cache

TICK_SECONDS = 0.5
KEEPALIVE_SECONDS = 15.0

router = APIRouter()


def changed_updates(cache: PriceCache, sent: dict[str, float]) -> list[dict]:
    """Updates whose price differs from what this client was last sent; records them in `sent`."""
    changed = [u for ticker, u in cache.all().items() if sent.get(ticker) != u.price]
    sent.update({u.ticker: u.price for u in changed})
    return [u.to_dict() for u in changed]


@router.get("/api/stream/prices", response_class=EventSourceResponse)
async def stream_prices() -> AsyncIterable[ServerSentEvent]:
    """Every tick, emit the changed tickers as one array; comment keepalive every ~15s."""
    sent: dict[str, float] = {}
    last_keepalive = time.monotonic()
    while True:
        if changed := changed_updates(price_cache, sent):
            yield ServerSentEvent(data=changed)
        if time.monotonic() - last_keepalive >= KEEPALIVE_SECONDS:
            yield ServerSentEvent(comment="keepalive")
            last_keepalive = time.monotonic()
        await asyncio.sleep(TICK_SECONDS)
