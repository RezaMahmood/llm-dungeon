"""Unit tests for llm_service.py, mocking OpenAIChatCompletionClient.get_response — no live
Azure OpenAI call (research.md §1). ChatResponse itself is real (not mocked) so `.value`'s
actual JSON/schema parsing is exercised for real."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_framework import ChatResponse, Message, UsageDetails

from backend.services.llm_service import (
    LLMOutputError,
    LLMService,
    _ExchangeResponse,
    _GenerationResponse,
)


def _mock_response(payload_json: str, response_format, prompt_tokens: int = 42, completion_tokens: int = 17):
    return ChatResponse(
        messages=[Message(role="assistant", contents=[payload_json])],
        usage_details=UsageDetails(input_token_count=prompt_tokens, output_token_count=completion_tokens),
        response_format=response_format,
    )


def _service_with_response(response: ChatResponse) -> LLMService:
    client = MagicMock()
    client.get_response = AsyncMock(return_value=response)
    return LLMService(client=client)


def test_generate_exchange_response_parses_valid_json():
    response = _mock_response(
        json.dumps({"assistantMessage": "Who is the player?", "fieldUpdates": {"worldPrompt": "A lighthouse..."}}),
        _ExchangeResponse,
    )
    service = _service_with_response(response)

    result = service.generate_exchange_response({"worldPrompt": None}, "A half-abandoned lighthouse...")

    assert result == {"assistantMessage": "Who is the player?", "fieldUpdates": {"worldPrompt": "A lighthouse..."}}
    service.client.get_response.assert_called_once()


def test_generate_story_config_parses_valid_json():
    response = _mock_response(json.dumps({"narrativeGuidance": "Keep it eerie but safe."}), _GenerationResponse)
    service = _service_with_response(response)

    result = service.generate_story_config({"worldPrompt": "A lighthouse..."})

    assert result == {"narrativeGuidance": "Keep it eerie but safe."}


def test_generate_exchange_response_rejects_malformed_json():
    response = _mock_response("not valid json{", _ExchangeResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.generate_exchange_response({}, "hello")


def test_generate_story_config_rejects_missing_required_key():
    response = _mock_response(json.dumps({"somethingElse": "oops"}), _GenerationResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.generate_story_config({})


def test_call_populates_span_attributes_from_usage():
    response = _mock_response(
        json.dumps({"assistantMessage": "hi", "fieldUpdates": {}}),
        _ExchangeResponse,
        prompt_tokens=100,
        completion_tokens=50,
    )
    service = _service_with_response(response)

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
