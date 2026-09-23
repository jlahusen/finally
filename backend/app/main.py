"""FastAPI application: lifespan-managed market data and background tasks, API routes, static SPA."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException  # noqa: E402

from app import tasks  # noqa: E402
from app.routes import router as api_router  # noqa: E402
from llm.routes import router as chat_router  # noqa: E402
from market.cache import price_cache  # noqa: E402
from market.factory import create_source  # noqa: E402
from market.stream import router as stream_router  # noqa: E402
from watchlist.service import tracked_tickers  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the market source and background loops; save prices and stop them on shutdown."""
    tickers = sorted(tracked_tickers())
    source = await create_source(price_cache, tasks.load_last_prices(), tickers)
    for ticker in tickers:
        price_cache.track(ticker)
    running = [
        asyncio.create_task(coro)
        for coro in (source.run(), tasks.snapshot_loop(), tasks.save_prices_loop())
    ]
    yield
    for task in running:
        task.cancel()
    await asyncio.gather(*running, return_exceptions=True)
    tasks.save_last_prices()
    await source.close()


class SPAStaticFiles(StaticFiles):
    """Static files that fall back to index.html for unknown non-API paths."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.startswith("api"):
                raise
            return await super().get_response("index.html", scope)


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(api_router)
app.include_router(stream_router)
app.include_router(chat_router)

if STATIC_DIR.is_dir():
    app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="static")
