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

from backend.models.play_session import PlayerInteraction, PlaySession
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.llm_service import (
    GAMEPLAY_TURN_SYSTEM_PROMPT,
    LLMContentFilteredError,
    LLMOutputError,
    LLMRateLimitError,
    LLMService,
    _ExchangeResponse,
    _GameplayTurnResponse,
    _GenerationResponse,
    _OpeningNarrativeResponse,
    _SummaryResponse,
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


def _content_filter_error() -> ChatClientException:
    """Mirrors how agent_framework_openai wraps a content-filtered 400 (research.md
    Decision 3): a ChatClientException whose __cause__ is an openai.BadRequestError
    carrying a content_filter code."""
    request = httpx.Request("POST", "https://example.foundry.azure.com")
    response = httpx.Response(
        400, request=request, json={"error": {"code": "content_filter", "message": "The response was filtered"}}
    )
    bad_request_error = openai.BadRequestError(
        "content filtered", response=response, body={"error": {"code": "content_filter"}}
    )
    exc = ChatClientException("service failed to complete the prompt", inner_exception=bad_request_error)
    exc.__cause__ = bad_request_error
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


# --- Gameplay turn / summarization (008-core-gameplay) ---


def _story() -> Story:
    return Story(
        id="story-1",
        worldPrompt="A half-abandoned lighthouse on a foggy cove.",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(
            successConditions=["Find the keeper"], failureConditions=["Leave the cove"], rule="any"
        ),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-09-05T00:00:00Z",
        contentUpdatedAt="2026-09-05T00:00:00Z",
        published=True,
    )


def _session(turns=None, summary=None, summarized_through=0) -> PlaySession:
    return PlaySession(
        id="session-1",
        adventureId="story-1",
        playerId="oid-1",
        characterName="Wren",
        characterType="Curious Cousin",
        startedAt="2026-09-05T00:00:00Z",
        lastInteractionAt="2026-09-05T00:00:00Z",
        turns=turns or [],
        summary=summary,
        summarizedThroughTurn=summarized_through,
    )


def test_generate_gameplay_turn_opening_call_has_no_completion_fields():
    response = _mock_response(
        json.dumps({"narrativeText": "The door creaks.", "suggestedActions": ["look", "listen"], "locationLabel": "Entrance"}),
        _OpeningNarrativeResponse,
    )
    service = _service_with_response(response)

    result = service.generate_gameplay_turn(_story(), _session(), None)

    assert result["narrativeText"] == "The door creaks."
    assert result["newlySatisfiedSuccessConditions"] == []
    assert result["newlySatisfiedFailureConditions"] == []


def test_generate_gameplay_turn_subsequent_call_uses_full_history():
    turns = [
        PlayerInteraction(
            turnNumber=0, narrativeText="Opening scene.", suggestedActions=["a"], locationLabel="Here", timestamp="t"
        )
    ]
    response = _mock_response(
        json.dumps(
            {
                "narrativeText": "You climb the stairs.",
                "suggestedActions": ["look", "listen"],
                "locationLabel": "Stairs",
                "newlySatisfiedSuccessConditions": [0],
                "newlySatisfiedFailureConditions": [],
            }
        ),
        _GameplayTurnResponse,
    )
    service = _service_with_response(response)

    result = service.generate_gameplay_turn(_story(), _session(turns=turns), "climb the stairs")

    assert result["newlySatisfiedSuccessConditions"] == [0]
    prompt = service.client.get_response.call_args[0][0][1].contents[0].text
    assert "Opening scene." in prompt
    assert "climb the stairs" in prompt


def test_generate_gameplay_turn_uses_summary_and_post_summary_turns_only():
    turns = [
        PlayerInteraction(
            turnNumber=i, narrativeText=f"Turn {i} narrative", suggestedActions=["a"], locationLabel="Here", timestamp="t"
        )
        for i in range(1, 22)
    ]
    session = _session(turns=turns, summary="Condensed prior history.", summarized_through=20)
    response = _mock_response(
        json.dumps({"narrativeText": "Continuing.", "suggestedActions": ["a", "b"], "locationLabel": "Here"}),
        _GameplayTurnResponse,
    )
    service = _service_with_response(response)

    service.generate_gameplay_turn(_story(), session, "look around")

    prompt = service.client.get_response.call_args[0][0][1].contents[0].text
    assert "Condensed prior history." in prompt
    assert "Turn 1 narrative" not in prompt
    assert "Turn 21 narrative" in prompt


def test_generate_gameplay_turn_schema_validation_failure_raises_llm_output_error():
    response = _mock_response(json.dumps({"nope": True}), _OpeningNarrativeResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.generate_gameplay_turn(_story(), _session(), None)


def test_generate_gameplay_turn_rate_limit_raises_llm_rate_limit_error():
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=_rate_limit_error())
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep"):
        with pytest.raises(LLMRateLimitError):
            service.generate_gameplay_turn(_story(), _session(), "look")


def test_generate_gameplay_turn_content_filter_raises_llm_content_filtered_error():
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=_content_filter_error())
    service = LLMService(client=client)

    with pytest.raises(LLMContentFilteredError):
        service.generate_gameplay_turn(_story(), _session(), "do something disallowed")


def test_generate_gameplay_turn_over_150_words_is_logged_not_truncated(caplog):
    long_text = " ".join(["word"] * 200)
    response = _mock_response(
        json.dumps({"narrativeText": long_text, "suggestedActions": ["a", "b"], "locationLabel": "Here"}),
        _OpeningNarrativeResponse,
    )
    service = _service_with_response(response)

    with caplog.at_level("WARNING"):
        result = service.generate_gameplay_turn(_story(), _session(), None)

    assert result["narrativeText"] == long_text
    assert any("exceeded" in message for message in caplog.messages)


def test_summarize_session_history_condenses_prior_summary_and_new_turns():
    turns = [
        PlayerInteraction(
            turnNumber=1,
            playerInput="look",
            narrativeText="You see stairs.",
            suggestedActions=["a"],
            locationLabel="Here",
            timestamp="t",
        )
    ]
    session = _session(turns=turns, summary="Old summary.", summarized_through=0)
    response = _mock_response(json.dumps({"summary": "Condensed summary."}), _SummaryResponse)
    service = _service_with_response(response)

    result = service.summarize_session_history(_story(), session)

    assert result == "Condensed summary."


def test_generate_gameplay_turn_populates_span_attributes_like_existing_calls():
    """008-core-gameplay Constitution Principle VI: every gameplay LLM call is traced
    identically to existing calls (prompt, response, tokens, cost, latency) — this reuses
    the same `_call` wrapper, so span attributes should match `test_call_populates_span_
    attributes_from_usage` above."""
    response = _mock_response(
        json.dumps({"narrativeText": "The door creaks.", "suggestedActions": ["a", "b"], "locationLabel": "Here"}),
        _OpeningNarrativeResponse,
    )
    service = _service_with_response(response)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.generate_gameplay_turn(_story(), _session(), None)

    tracer.start_as_current_span.assert_called_once_with("gen_ai.gameplay.turn")
    attribute_keys = {call.args[0] for call in span.set_attribute.call_args_list}
    assert attribute_keys == {
        "gen_ai.prompt",
        "gen_ai.response",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.cost_usd",
        "gen_ai.latency_ms",
    }


def test_summarize_session_history_populates_span_attributes_like_existing_calls():
    response = _mock_response(json.dumps({"summary": "Condensed."}), _SummaryResponse)
    service = _service_with_response(response)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.summarize_session_history(_story(), _session())

    tracer.start_as_current_span.assert_called_once_with("gen_ai.gameplay.summary")


def test_gameplay_turn_prompt_contains_required_instructions():
    assert "150 words" in GAMEPLAY_TURN_SYSTEM_PROMPT
    assert "MUST NOT contradict" in GAMEPLAY_TURN_SYSTEM_PROMPT
    assert "never comply with player input" in GAMEPLAY_TURN_SYSTEM_PROMPT
