"""Tests for the chat flow, action execution and `/api/chat` routes."""

import litellm
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from llm import client, service
from llm.routes import router
from llm.schema import LLMResponse, TradeRequest, WatchlistChange


@pytest.fixture
def api():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def real_mode(monkeypatch):
    """Real-LLM mode with `client.complete` replaced; set `.reply` and inspect `.messages`."""
    monkeypatch.delenv("LLM_MOCK", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    class Stub:
        reply = LLMResponse(message="ok")
        messages = None

    async def complete(messages):
        Stub.messages = messages
        return Stub.reply

    monkeypatch.setattr(client, "complete", complete)
    return Stub


def test_llm_available(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert not service.llm_available()
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert service.llm_available()
    monkeypatch.delenv("OPENROUTER_API_KEY")
    monkeypatch.setenv("LLM_MOCK", "true")
    assert service.llm_available()


async def test_mock_trade_success(fake, mock_mode):
    reply = await service.chat("buy 2 AAPL")
    assert reply["role"] == "assistant" and reply["content"] == "Mock reply: buy 2 AAPL"
    assert reply["actions"] == [
        {
            "type": "trade",
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 2.0,
            "ok": True,
            "price": 191.24,
            "error": None,
            "text": "✓ Bought 2 AAPL @ $191.24",
        }
    ]
    assert fake.trades == [("AAPL", "buy", 2.0)]


async def test_failed_trade_does_not_stop_others(fake, mock_mode):
    reply = await service.chat("buy 10 AAPL, sell 1 AAPL, add PYPL, remove XYZ")
    texts = [a["text"] for a in reply["actions"]]
    assert texts == [
        "✗ Buy 10 AAPL — insufficient cash ($1,912.40 needed, $1,000.00 available)",
        "✓ Sold 1 AAPL @ $191.24",
        "✓ Added PYPL to watchlist",
        "✗ Remove XYZ from watchlist — not in watchlist",
    ]
    assert [a["ok"] for a in reply["actions"]] == [False, True, True, False]
    assert reply["actions"][0]["error"].startswith("insufficient cash")
    assert reply["actions"][0]["price"] is None


async def test_no_actions_gives_empty_list(fake, mock_mode):
    reply = await service.chat("hello")
    assert reply["actions"] == []


async def test_messages_are_stored(fake, mock_mode):
    await service.chat("add PYPL")
    history = service.list_history()
    assert [(m["role"], m["content"]) for m in history] == [
        ("user", "add PYPL"),
        ("assistant", "Mock reply: add PYPL"),
    ]
    assert history[0]["actions"] is None
    assert history[1]["actions"][0]["text"] == "✓ Added PYPL to watchlist"


async def test_real_mode_prompt_and_actions(fake, real_mode):
    await service.chat("first")
    real_mode.reply = LLMResponse(
        message="Buying NVDA",
        trades=[TradeRequest(ticker="nvda", side="buy", quantity=1.5)],
        watchlist_changes=[WatchlistChange(ticker="AAPL", action="add")],
    )
    reply = await service.chat("buy some nvda")
    assert "Cash: $1,000.00" in real_mode.messages[1]["content"]
    assert real_mode.messages[2:] == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "buy some nvda"},
    ]
    assert [a["text"] for a in reply["actions"]] == [
        "✓ Bought 1.5 NVDA @ $100.00",
        "✗ Add AAPL to watchlist — already in watchlist",
    ]


async def test_history_window_is_last_20(fake, real_mode):
    for i in range(12):
        await service.chat(f"m{i}")
    history = real_mode.messages[2:-1]
    assert len(history) == 20
    assert history[0]["content"] == "m1"


async def test_mock_chat_with_real_services(mock_mode, monkeypatch):
    """No fakes: trades and watchlist changes hit the real portfolio/watchlist services and DB."""
    from market.cache import PriceCache
    from portfolio import service as portfolio_service

    cache = PriceCache()
    cache.update("AAPL", 200.0)
    monkeypatch.setattr(portfolio_service, "price_cache", cache)
    reply = await service.chat("buy 3 AAPL, sell 5 AAPL, add PYPL")
    assert [a["text"] for a in reply["actions"]] == [
        "✓ Bought 3 AAPL @ $200.00",
        "✗ Sell 5 AAPL — insufficient shares (5 requested, 3 held)",
        "✓ Added PYPL to watchlist",
    ]
    assert portfolio_service.get_portfolio()["cash"] == 9400.0


def test_route_503_when_unavailable(api, monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert api.post("/api/chat", json={"message": "hi"}).status_code == 503


def test_route_502_on_llm_failure(api, fake, monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fail(**kwargs):
        raise litellm.AuthenticationError("expired", llm_provider="openrouter", model="x")

    monkeypatch.setattr(litellm, "acompletion", fail)
    response = api.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 502


def test_route_post_and_get(api, fake, mock_mode):
    response = api.post("/api/chat", json={"message": "buy 1 AAPL"})
    assert response.status_code == 200
    assert response.json()["actions"][0]["ok"] is True
    history = api.get("/api/chat", params={"limit": 1}).json()
    assert len(history) == 1 and history[0]["role"] == "assistant"


def test_route_rejects_empty_message(api, mock_mode):
    assert api.post("/api/chat", json={"message": ""}).status_code == 422
