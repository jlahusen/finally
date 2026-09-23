"""LiteLLM client for OpenRouter with structured output."""

import litellm

from llm.schema import LLMResponse, parse_response

MODEL = "openrouter/@preset/finy"

# LiteLLM's capability lookup can't resolve "@preset/finy" and prints a harmless "Provider List" banner.
litellm.suppress_debug_info = True


async def complete(messages: list[dict]) -> LLMResponse:
    """Call the model with the `LLMResponse` schema as `response_format` and parse the reply.

    The API key is read by LiteLLM from `OPENROUTER_API_KEY`.
    """
    response = await litellm.acompletion(model=MODEL, messages=messages, response_format=LLMResponse)
    return parse_response(response.choices[0].message.content)
