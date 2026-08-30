"""Unit tests for llm_service.py, mocking ChatCompletionsClient — no live Foundry call
(research.md §1)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.services.llm_service import LLMOutputError, LLMService


def _mock_response(content: str, prompt_tokens: int = 42, completion_tokens: int = 17):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    response.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return response


def test_generate_exchange_response_parses_valid_json():
    client = MagicMock()
    client.complete.return_value = _mock_response(
        json.dumps({"assistantMessage": "Who is the player?", "fieldUpdates": {"worldPrompt": "A lighthouse..."}})
    )
    service = LLMService(client=client)

    result = service.generate_exchange_response({"worldPrompt": None}, "A half-abandoned lighthouse...")

    assert result == {"assistantMessage": "Who is the player?", "fieldUpdates": {"worldPrompt": "A lighthouse..."}}
    client.complete.assert_called_once()


def test_generate_story_config_parses_valid_json():
    client = MagicMock()
    client.complete.return_value = _mock_response(json.dumps({"narrativeGuidance": "Keep it eerie but safe."}))
    service = LLMService(client=client)

    result = service.generate_story_config({"worldPrompt": "A lighthouse..."})

    assert result == {"narrativeGuidance": "Keep it eerie but safe."}


def test_generate_exchange_response_rejects_malformed_json():
    client = MagicMock()
    client.complete.return_value = _mock_response("not valid json{")
    service = LLMService(client=client)

    with pytest.raises(LLMOutputError):
        service.generate_exchange_response({}, "hello")


def test_generate_story_config_rejects_missing_required_key():
    client = MagicMock()
    client.complete.return_value = _mock_response(json.dumps({"somethingElse": "oops"}))
    service = LLMService(client=client)

    with pytest.raises(LLMOutputError):
        service.generate_story_config({})


def test_call_populates_span_attributes_from_usage():
    client = MagicMock()
    client.complete.return_value = _mock_response(
        json.dumps({"assistantMessage": "hi", "fieldUpdates": {}}),
        prompt_tokens=100,
        completion_tokens=50,
    )
    service = LLMService(client=client)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.generate_exchange_response({}, "hello")

    tracer.start_as_current_span.assert_called_once_with("gen_ai.story_creation.exchange")
    attribute_keys = {call.args[0] for call in span.set_attribute.call_args_list}
    assert attribute_keys == {
        "gen_ai.prompt",
        "gen_ai.response",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.cost_usd",
        "gen_ai.latency_ms",
    }
    attributes = {call.args[0]: call.args[1] for call in span.set_attribute.call_args_list}
    assert attributes["gen_ai.usage.input_tokens"] == 100
    assert attributes["gen_ai.usage.output_tokens"] == 50
