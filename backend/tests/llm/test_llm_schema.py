"""Tests for structured output parsing."""

import json

from llm.schema import LLMResponse, parse_response


def test_message_only():
    result = parse_response('{"message": "Hello"}')
    assert result == LLMResponse(message="Hello")


def test_full_response():
    raw = json.dumps(
        {
            "message": "Done",
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
            "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
        }
    )
    result = parse_response(raw)
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].quantity == 10.0
    assert result.watchlist_changes[0].action == "add"


def test_empty_action_lists():
    result = parse_response('{"message": "Hi", "trades": [], "watchlist_changes": []}')
    assert result.trades == [] and result.watchlist_changes == []


def test_fractional_quantity():
    result = parse_response('{"message": "x", "trades": [{"ticker": "V", "side": "sell", "quantity": 0.5}]}')
    assert result.trades[0].quantity == 0.5


def test_not_json_becomes_message():
    assert parse_response("  just text  ") == LLMResponse(message="just text")


def test_invalid_actions_keep_message():
    raw = '{"message": "Trying", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}]}'
    assert parse_response(raw) == LLMResponse(message="Trying")


def test_json_without_message_becomes_raw_text():
    assert parse_response('{"foo": 1}').message == '{"foo": 1}'


def test_json_array_becomes_raw_text():
    assert parse_response("[1, 2]").message == "[1, 2]"
