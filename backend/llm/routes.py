"""`/api/chat` endpoints."""

import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from llm import service

router = APIRouter()


class ChatRequest(BaseModel):
    """Body of `POST /api/chat`."""

    message: str = Field(min_length=1)


@router.get("/api/chat")
def get_chat(limit: int = 50) -> list[dict]:
    """Recent conversation history, oldest first."""
    return service.list_history(limit)


@router.post("/api/chat")
async def post_chat(request: ChatRequest) -> dict:
    """Send a message and return the assistant's reply with executed actions."""
    if not service.llm_available():
        raise HTTPException(503, "AI assistant unavailable — no API key configured")
    try:
        return await service.chat(request.message)
    except openai.APIError as error:
        raise HTTPException(502, f"LLM call failed: {error}") from error
