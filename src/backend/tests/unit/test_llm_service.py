"""Unit tests for llm_service.py, mocking OpenAIChatCompletionClient.get_response — no live
Azure OpenAI call (research.md §1). ChatResponse itself is real (not mocked) so `.value`'s
actual JSON/schema parsing is exercised for real."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_framework import ChatResponse, Message, UsageDetails

from backend.services.llm_service import LLMOutputError, LLMService, _OutlineResponse


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


def test_suggest_outline_parses_valid_json():
    response = _mock_response(json.dumps({"outline": "A half-abandoned lighthouse..."}), _OutlineResponse)
    service = _service_with_response(response)

    result = service.suggest_outline("A lighthouse mystery in 1908")

    assert result == "A half-abandoned lighthouse..."
    service.client.get_response.assert_called_once()


def test_suggest_outline_rejects_malformed_json():
    response = _mock_response("not valid json{", _OutlineResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.suggest_outline("hello")


def test_suggest_outline_rejects_missing_required_key():
    response = _mock_response(json.dumps({"somethingElse": "oops"}), _OutlineResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.suggest_outline("hello")


def test_suggest_outline_rejects_empty_outline():
    response = _mock_response(json.dumps({"outline": ""}), _OutlineResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.suggest_outline("hello")


def test_call_populates_span_attributes_from_usage():
    response = _mock_response(
        json.dumps({"outline": "A half-abandoned lighthouse..."}),
        _OutlineResponse,
        prompt_tokens=100,
        completion_tokens=50,
    )
    service = _service_with_response(response)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.suggest_outline("hello")

    tracer.start_as_current_span.assert_called_once_with("gen_ai.story_creation.suggest_outline")
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
