"""HTTP routes via TestClient, with the simulator running under the app lifespan."""

import time
from contextlib import closing

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import tasks
from app.main import SPAStaticFiles, app
from db import repository as repo
from db.database import get_connection
from market import stream
from market.cache import price_cache
from market.stream import stream_prices


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    with TestClient(app) as test_client:
        wait_for_price(test_client, "AAPL")
        yield test_client


def wait_for_price(client, ticker):
    for _ in range(50):
        if price_cache.get(ticker):
            return
        time.sleep(0.05)
    raise AssertionError(f"no price for {ticker}")


def test_health(client, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    assert client.get("/api/health").json() == {"status": "ok", "llm_available": True}


def test_fresh_portfolio(client):
    assert client.get("/api/portfolio").json() == {
        "cash": 10000.0, "total_value": 10000.0, "unrealized_pnl": 0.0, "positions": []
    }


def test_trade_round_trip(client):
    response = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 2, "side": "buy"})
    assert response.status_code == 200
    body = response.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["portfolio"]["positions"][0]["ticker"] == "AAPL"
    assert client.get("/api/trades").json()[0]["id"] == body["trade"]["id"]
    assert len(client.get("/api/portfolio/history").json()) == 1

    sell = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "sell"})
    assert (sell.status_code, sell.json()) == (400, {"detail": "insufficient shares (5 requested, 2 held)"})


def test_trade_rejects_bad_side(client):
    assert client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "hold"}).status_code == 422


def test_watchlist_crud(client):
    tickers = [row["ticker"] for row in client.get("/api/watchlist").json()]
    assert tickers[:3] == ["AAPL", "GOOGL", "MSFT"] and len(tickers) == 10

    added = client.post("/api/watchlist", json={"ticker": " pypl "})
    assert (added.status_code, added.json()["ticker"]) == (201, "PYPL")
    assert client.post("/api/watchlist", json={"ticker": "PYPL"}).status_code == 409
    assert client.post("/api/watchlist", json={"ticker": "not a ticker"}).status_code == 422

    assert client.delete("/api/watchlist/pypl").status_code == 204
    assert client.delete("/api/watchlist/PYPL").status_code == 404


async def test_price_stream_first_event_is_full_array():
    price_cache.update("AAPL", 190.0)
    events = stream_prices()
    event = await anext(events)
    await events.aclose()
    assert any(u["ticker"] == "AAPL" and u["price"] == 190.0 for u in event.data)


def test_shutdown_saves_prices_and_restart_resumes(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    with TestClient(app):
        wait_for_price(None, "AAPL")
    saved = tasks.load_last_prices()
    assert saved["AAPL"] == price_cache.get("AAPL").price

    price_cache.untrack("AAPL")
    with closing(get_connection()) as conn, conn:
        repo.save_last_prices(conn, {"AAPL": 321.0})
    with TestClient(app):
        wait_for_price(None, "AAPL")
        assert price_cache.get("AAPL").open_price == 321.0


async def test_stream_sends_keepalive_comment(monkeypatch):
    monkeypatch.setattr(stream, "KEEPALIVE_SECONDS", 0.0)
    price_cache.update("AAPL", 190.0)
    events = stream_prices()
    first, second = await anext(events), await anext(events)
    await events.aclose()
    assert first.data and second.comment == "keepalive"


def test_spa_fallback_serves_index(tmp_path):
    (tmp_path / "index.html").write_text("<html>spa</html>")
    spa = FastAPI()
    spa.mount("/", SPAStaticFiles(directory=tmp_path, html=True))
    client = TestClient(spa)
    assert client.get("/").text == "<html>spa</html>"
    assert client.get("/some/page").text == "<html>spa</html>"
    assert client.get("/api/missing").status_code == 404
