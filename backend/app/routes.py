"""Portfolio, trade, watchlist and health endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, BeforeValidator, StringConstraints

from llm.service import llm_available
from portfolio import service as portfolio
from watchlist import service as watchlist

Ticker = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z][A-Z0-9.\-]{0,9}$"),
    BeforeValidator(lambda value: value.strip().upper() if isinstance(value, str) else value),
]

router = APIRouter(prefix="/api")


class TradeRequest(BaseModel):
    """Body of `POST /api/portfolio/trade`."""

    ticker: str
    quantity: float
    side: Literal["buy", "sell"]


class WatchlistRequest(BaseModel):
    """Body of `POST /api/watchlist`."""

    ticker: Ticker


@router.get("/health")
def health() -> dict:
    """Liveness plus whether the chat assistant can be used."""
    return {"status": "ok", "llm_available": llm_available()}


@router.get("/portfolio")
def get_portfolio() -> dict:
    """Cash, valued positions, total value and unrealized P&L."""
    return portfolio.get_portfolio()


@router.post("/portfolio/trade")
def trade(request: TradeRequest) -> dict:
    """Execute a market order; 400 with the validation message on failure."""
    try:
        executed = portfolio.execute_trade(request.ticker, request.side, request.quantity)
    except portfolio.TradeError as error:
        raise HTTPException(400, str(error)) from error
    return {"trade": executed, "portfolio": portfolio.get_portfolio()}


@router.get("/portfolio/history")
def history(limit: int = 200) -> list[dict]:
    """Portfolio value over time, oldest first."""
    return portfolio.history(limit)


@router.get("/trades")
def trades(limit: int = 50) -> list[dict]:
    """Trade history, newest first."""
    return portfolio.trades(limit)


@router.get("/watchlist")
def list_watchlist() -> list[dict]:
    """Watchlist tickers with latest prices."""
    return watchlist.list_items()


@router.post("/watchlist", status_code=201)
def add_watchlist(request: WatchlistRequest) -> dict:
    """Add a ticker; 409 if already present."""
    if not watchlist.add(request.ticker):
        raise HTTPException(409, f"{request.ticker} is already in the watchlist")
    return watchlist.item(request.ticker)


@router.delete("/watchlist/{ticker}", status_code=204)
def remove_watchlist(ticker: str) -> Response:
    """Remove a ticker; 404 if absent."""
    if not watchlist.remove(ticker):
        raise HTTPException(404, f"{ticker.upper()} is not in the watchlist")
    return Response(status_code=204)
