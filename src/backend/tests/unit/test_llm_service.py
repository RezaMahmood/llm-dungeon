"""Unit tests for llm_service.py, mocking OpenAIChatCompletionClient.get_response — no live
Azure OpenAI call (research.md §1). ChatResponse itself is real (not mocked) so `.value`'s
actual JSON/schema parsing is exercised for real."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest
from agent_framework import ChatResponse, Message, UsageDetails
from agent_framework.exceptions import ChatClientException

from backend.services.llm_service import (
    LLMOutputError,
    LLMRateLimitError,
    LLMService,
    _ExchangeResponse,
    _GenerationResponse,
)


def _rate_limit_error(retry_after: str | None = None) -> ChatClientException:
    """Mirrors how agent_framework_openai wraps a 429: a ChatClientException whose
    __cause__ is the underlying openai.RateLimitError (#33)."""
    request = httpx.Request("POST", "https://example.foundry.azure.com")
    headers = {"retry-after": retry_after} if retry_after else {}
    response = httpx.Response(429, request=request, headers=headers, json={"error": {"message": "rate limited"}})
    rate_limit_error = openai.RateLimitError("rate limited", response=response, body=None)
    exc = ChatClientException("service failed to complete the prompt", inner_exception=rate_limit_error)
    exc.__cause__ = rate_limit_error
    return exc


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


# --- Rate limiting (#33) ---


def test_call_retries_then_succeeds_after_transient_rate_limit():
    response = _mock_response(json.dumps({"assistantMessage": "hi", "fieldUpdates": {}}), _ExchangeResponse)
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=[_rate_limit_error(), response])
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep") as sleep:
        result = service.generate_exchange_response({}, "hello")

    assert result == {"assistantMessage": "hi", "fieldUpdates": {}}
    assert client.get_response.call_count == 2
    sleep.assert_called_once()


def test_call_raises_rate_limit_error_after_exhausting_retries():
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=_rate_limit_error())
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep"):
        with pytest.raises(LLMRateLimitError):
            service.generate_exchange_response({}, "hello")

    assert client.get_response.call_count == 3


def test_call_honors_retry_after_header():
    response = _mock_response(json.dumps({"assistantMessage": "hi", "fieldUpdates": {}}), _ExchangeResponse)
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=[_rate_limit_error(retry_after="7"), response])
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep") as sleep:
        service.generate_exchange_response({}, "hello")

    sleep.assert_called_once_with(7.0)


def test_call_does_not_retry_non_rate_limit_errors():
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=RuntimeError("boom"))
    service = LLMService(client=client)

    with pytest.raises(RuntimeError, match="boom"):
        service.generate_exchange_response({}, "hello")

    assert client.get_response.call_count == 1
