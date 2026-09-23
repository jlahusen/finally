"""Chat service: availability, history and the full message -> LLM -> actions flow."""

import os
from contextlib import closing

from db import repository
from db.database import get_connection
from llm import client
from llm.actions import run_actions
from llm.mock import mock_response
from llm.prompt import build_context, build_messages
from llm.schema import LLMResponse
from portfolio import service as portfolio_service
from watchlist import service as watchlist_service

HISTORY_WINDOW = 20


def mock_enabled() -> bool:
    """True when `LLM_MOCK=true`."""
    return os.environ.get("LLM_MOCK", "").lower() == "true"


def llm_available() -> bool:
    """True when mock mode is on or an OpenRouter key is configured."""
    return mock_enabled() or bool(os.environ.get("OPENROUTER_API_KEY"))


def list_history(limit: int = 50) -> list[dict]:
    """The latest `limit` chat messages, oldest first."""
    with closing(get_connection()) as conn:
        return repository.list_chat_messages(conn, limit)


def _store(role: str, content: str, actions: list | None) -> dict:
    with closing(get_connection()) as conn, conn:
        return repository.insert_chat_message(conn, role, content, actions)


async def _reply(user_message: str, history: list[dict]) -> LLMResponse:
    """Ask the mock or the real model for a structured reply."""
    if mock_enabled():
        return mock_response(user_message)
    context = build_context(portfolio_service.get_portfolio(), watchlist_service.list_items())
    return await client.complete(build_messages(context, history, user_message))


async def chat(user_message: str) -> dict:
    """Store the user message, get a reply, execute its actions once and store the assistant message."""
    history = list_history(HISTORY_WINDOW)
    _store("user", user_message, None)
    response = await _reply(user_message, history)
    return _store("assistant", response.message, run_actions(response))
