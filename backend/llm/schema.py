"""Structured output schema for the assistant and lenient parsing of raw model output."""

import json
from typing import Literal

from pydantic import BaseModel, ValidationError


class TradeRequest(BaseModel):
    """A market order the assistant wants executed."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    """A watchlist add or remove the assistant wants applied."""

    ticker: str
    action: Literal["add", "remove"]


class LLMResponse(BaseModel):
    """The assistant's full reply: a message plus optional actions."""

    message: str
    trades: list[TradeRequest] = []
    watchlist_changes: list[WatchlistChange] = []


def parse_response(raw: str) -> LLMResponse:
    """Parse model output into an `LLMResponse`, degrading to a message-only reply.

    Valid JSON with bad action items keeps its `message` and drops the actions;
    non-JSON output becomes the message verbatim.
    """
    try:
        return LLMResponse.model_validate_json(raw)
    except ValidationError:
        pass
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return LLMResponse(message=raw.strip())
    if isinstance(data, dict) and isinstance(data.get("message"), str):
        return LLMResponse(message=data["message"])
    return LLMResponse(message=raw.strip())
