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
from backend.services import llm_service as llm_service_module
from backend.services.llm_service import config as llm_service_config
from backend.services.llm_service import (
    GAMEPLAY_TURN_SYSTEM_PROMPT,
    LLMContentFilteredError,
    LLMOutputError,
    LLMRateLimitError,
    LLMService,
    _GameplayTurnResponse,
    _GenerationResponse,
    _StartingPointResponse,
    _SummaryResponse,
    _WorldPromptResponse,
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


def test_suggest_world_prompt_returns_the_single_suggested_prompt():
    response = _mock_response(json.dumps({"worldPrompt": "A lighthouse..."}), _WorldPromptResponse)
    service = _service_with_response(response)

    result, tokens_used = service.suggest_world_prompt({"worldPrompt": None}, "A half-abandoned lighthouse...")

    assert result == "A lighthouse..."
    # 42 input + 17 output (_mock_response's defaults) — research.md Decision 1.
    assert tokens_used == 59
    # One pass, not a conversation (#227) — exactly one call, and nothing to follow up on.
    service.client.get_response.assert_called_once()


def test_generate_story_config_parses_valid_json():
    response = _mock_response(json.dumps({"narrativeGuidance": "Keep it eerie but safe."}), _GenerationResponse)
    service = _service_with_response(response)

    result, tokens_used = service.generate_story_config({"worldPrompt": "A lighthouse..."})

    assert result == {"narrativeGuidance": "Keep it eerie but safe."}
    assert tokens_used == 59


def test_suggest_world_prompt_rejects_malformed_json():
    response = _mock_response("not valid json{", _WorldPromptResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.suggest_world_prompt({}, "hello")


def test_generate_story_config_rejects_missing_required_key():
    response = _mock_response(json.dumps({"somethingElse": "oops"}), _GenerationResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.generate_story_config({})


def test_call_populates_span_attributes_from_usage():
    response = _mock_response(
        json.dumps({"worldPrompt": "A lighthouse..."}),
        _WorldPromptResponse,
        prompt_tokens=100,
        completion_tokens=50,
    )
    service = _service_with_response(response)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.suggest_world_prompt({}, "hello")

    tracer.start_as_current_span.assert_called_once_with("gen_ai.story_creation.world_prompt")
    attribute_keys = {call.args[0] for call in span.set_attribute.call_args_list}
    assert attribute_keys == {
        "gen_ai.prompt",
        "gen_ai.response",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.usage.reasoning_tokens",
        "gen_ai.cost_usd",
        "gen_ai.latency_ms",
    }
    attributes = {call.args[0]: call.args[1] for call in span.set_attribute.call_args_list}
    assert attributes["gen_ai.usage.input_tokens"] == 100
    assert attributes["gen_ai.usage.output_tokens"] == 50
    # A deployment that reports no reasoning breakdown records a zero, never a missing
    # attribute — the Application Insights query behind #285 can then treat the attribute
    # as always present.
    assert attributes["gen_ai.usage.reasoning_tokens"] == 0


def test_call_records_reasoning_tokens_when_the_deployment_reports_them():
    """gpt-5-nano bills reasoning as output tokens but never shows them in the response
    text, so the span attribute is the only way to see how much of a slow call was
    thinking rather than writing (#285)."""
    usage = UsageDetails(input_token_count=100, output_token_count=1200)
    usage["reasoning_output_token_count"] = 1024
    response = ChatResponse(
        messages=[Message(role="assistant", contents=[json.dumps({"worldPrompt": "A lighthouse..."})])],
        usage_details=usage,
        response_format=_WorldPromptResponse,
    )
    service = _service_with_response(response)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.suggest_world_prompt({}, "hello")

    attributes = {call.args[0]: call.args[1] for call in span.set_attribute.call_args_list}
    assert attributes["gen_ai.usage.reasoning_tokens"] == 1024
    # Reasoning tokens are a subset of the output count, so cost must not double-count them.
    assert attributes["gen_ai.usage.output_tokens"] == 1200


# --- Reasoning effort (#285) ---


def _options_sent(call, payload: dict, response_model, override: str = "") -> dict:
    """Runs one call with LLM_REASONING_EFFORT set to `override` and returns the options
    mapping actually handed to the underlying client."""
    response = _mock_response(json.dumps(payload), response_model)
    service = _service_with_response(response)
    with patch.object(llm_service_config, "LLM_REASONING_EFFORT", override):
        call(service)
    return service.client.get_response.call_args.kwargs["options"]


def _world_prompt_options(override: str = "") -> dict:
    return _options_sent(
        lambda service: service.suggest_world_prompt({}, "hello"),
        {"worldPrompt": "A lighthouse..."},
        _WorldPromptResponse,
        override,
    )


_TURN_PAYLOAD = {
    "narrativeText": "The door creaks.",
    "suggestedActions": ["go in", "wait"],
    "locationLabel": "Hall",
    "newlySatisfiedSuccessConditions": [],
    "newlySatisfiedFailureConditions": [],
}
_STARTING_POINT_PAYLOAD = {
    "narrativeText": "You arrive at the gate.",
    "suggestedActions": ["knock", "wait"],
    "locationLabel": "Gate",
}

# Every call site, with the effort it is supposed to ask for. Covers all five so a swapped
# or omitted constant fails here rather than silently shipping.
_CALL_SITES = [
    pytest.param(
        lambda service: service.suggest_world_prompt({}, "hello"),
        {"worldPrompt": "A lighthouse..."},
        _WorldPromptResponse,
        "minimal",
        id="world_prompt",
    ),
    pytest.param(
        lambda service: service.generate_story_config({"worldPrompt": "A lighthouse..."}),
        {"narrativeGuidance": "Keep it eerie but safe."},
        _GenerationResponse,
        "low",
        id="generation",
    ),
    pytest.param(
        lambda service: service.generate_starting_point({"worldPrompt": "A lighthouse..."}, "guidance"),
        _STARTING_POINT_PAYLOAD,
        _StartingPointResponse,
        "low",
        id="starting_point",
    ),
    pytest.param(
        lambda service: service.generate_gameplay_turn(_story(), _session(), "look"),
        _TURN_PAYLOAD,
        _GameplayTurnResponse,
        "medium",
        id="gameplay_turn",
    ),
    pytest.param(
        lambda service: service.summarize_session_history(_story(), _session()),
        {"summary": "Condensed."},
        _SummaryResponse,
        "minimal",
        id="gameplay_summary",
    ),
]


@pytest.mark.parametrize("call, payload, response_model, expected_effort", _CALL_SITES)
def test_each_call_site_asks_for_its_own_reasoning_effort(call, payload, response_model, expected_effort):
    """The gameplay turn decides whether the player's action satisfied a completion
    condition and that verdict is persisted, so it keeps a budget the prose calls do not."""
    options = _options_sent(call, payload, response_model)

    assert options["reasoning_effort"] == expected_effort
    # The response format must survive alongside it — the schema is what stops a call
    # returning prose instead of the JSON object its caller parses.
    assert options["response_format"] is response_model


def test_call_requires_an_explicit_reasoning_effort():
    """Belt and braces on the parameterization above: a call site added later cannot fall
    back to a default, it has to pick one."""
    import inspect

    signature = inspect.signature(LLMService._call)

    assert "reasoning_effort" in signature.parameters
    assert signature.parameters["reasoning_effort"].default is inspect.Parameter.empty


def test_the_override_replaces_every_call_default():
    options = _world_prompt_options(override="high")

    assert options["reasoning_effort"] == "high"


def test_the_off_override_omits_reasoning_effort_entirely():
    """A non-reasoning deployment rejects `reasoning_effort` outright, so this has to drop
    the parameter rather than send a value."""
    options = _world_prompt_options(override="off")

    assert "reasoning_effort" not in options
    assert options["response_format"] is _WorldPromptResponse


# --- Rate limiting (#33) ---


def test_call_retries_then_succeeds_after_transient_rate_limit():
    response = _mock_response(json.dumps({"worldPrompt": "A lighthouse..."}), _WorldPromptResponse)
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=[_rate_limit_error(), response])
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep") as sleep:
        result, _tokens_used = service.suggest_world_prompt({}, "hello")

    assert result == "A lighthouse..."
    assert client.get_response.call_count == 2
    sleep.assert_called_once()


def test_call_raises_rate_limit_error_after_exhausting_retries():
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=_rate_limit_error())
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep"):
        with pytest.raises(LLMRateLimitError):
            service.suggest_world_prompt({}, "hello")

    assert client.get_response.call_count == 3


def test_call_honors_retry_after_header():
    response = _mock_response(json.dumps({"worldPrompt": "A lighthouse..."}), _WorldPromptResponse)
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=[_rate_limit_error(retry_after="7"), response])
    service = LLMService(client=client)

    with patch("backend.services.llm_service.time.sleep") as sleep:
        service.suggest_world_prompt({}, "hello")

    sleep.assert_called_once_with(7.0)


def test_call_does_not_retry_non_rate_limit_errors():
    client = MagicMock()
    client.get_response = AsyncMock(side_effect=RuntimeError("boom"))
    service = LLMService(client=client)

    with pytest.raises(RuntimeError, match="boom"):
        service.suggest_world_prompt({}, "hello")

    assert client.get_response.call_count == 1


# --- Gameplay turn / summarization (008-core-gameplay-done) ---


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


def test_generate_starting_point_returns_the_opening_scene_and_carries_the_guidance():
    response = _mock_response(
        json.dumps(
            {
                "narrativeText": "The door creaks.",
                "suggestedActions": ["look", "listen"],
                "locationLabel": "Entrance",
            }
        ),
        _StartingPointResponse,
    )
    service = _service_with_response(response)

    result, tokens_used = service.generate_starting_point({"worldPrompt": "A lighthouse..."}, "Keep it eerie but safe.")

    assert result["narrativeText"] == "The door creaks."
    assert tokens_used == 59
    assert result["suggestedActions"] == ["look", "listen"]
    prompt = service.client.get_response.call_args[0][0][1].contents[0].text
    assert "Keep it eerie but safe." in prompt
    assert "A lighthouse..." in prompt


def test_generate_starting_point_has_no_completion_condition_fields():
    """#271: the opening scene is generated before any player has acted, so its schema
    structurally cannot report a satisfied success/failure condition."""
    assert "newlySatisfiedSuccessConditions" not in _StartingPointResponse.model_fields
    assert "newlySatisfiedFailureConditions" not in _StartingPointResponse.model_fields


def test_generate_starting_point_is_traced_under_its_own_span():
    response = _mock_response(
        json.dumps({"narrativeText": "The door creaks.", "suggestedActions": ["a", "b"], "locationLabel": "Here"}),
        _StartingPointResponse,
    )
    service = _service_with_response(response)
    tracer = MagicMock()

    with patch("backend.services.llm_service.tracer", tracer):
        service.generate_starting_point({"worldPrompt": "A lighthouse..."}, "Keep it eerie.")

    tracer.start_as_current_span.assert_called_once_with("gen_ai.story_creation.starting_point")


def test_generate_starting_point_rejects_malformed_output():
    response = _mock_response(json.dumps({"nope": True}), _StartingPointResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.generate_starting_point({}, "Keep it eerie.")


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

    result, tokens_used = service.generate_gameplay_turn(_story(), _session(turns=turns), "climb the stairs")

    assert result["newlySatisfiedSuccessConditions"] == [0]
    assert tokens_used == 59
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
    response = _mock_response(json.dumps({"nope": True}), _GameplayTurnResponse)
    service = _service_with_response(response)

    with pytest.raises(LLMOutputError):
        service.generate_gameplay_turn(_story(), _session(), "look")


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
        _GameplayTurnResponse,
    )
    service = _service_with_response(response)

    with caplog.at_level("WARNING"):
        result, _tokens_used = service.generate_gameplay_turn(_story(), _session(), "look")

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

    result, tokens_used = service.summarize_session_history(_story(), session)

    assert result == "Condensed summary."
    assert tokens_used == 59


def test_generate_gameplay_turn_populates_span_attributes_like_existing_calls():
    """008-core-gameplay-done Constitution Principle VI: every gameplay LLM call is traced
    identically to existing calls (prompt, response, tokens, cost, latency) — this reuses
    the same `_call` wrapper, so span attributes should match `test_call_populates_span_
    attributes_from_usage` above."""
    response = _mock_response(
        json.dumps({"narrativeText": "The door creaks.", "suggestedActions": ["a", "b"], "locationLabel": "Here"}),
        _GameplayTurnResponse,
    )
    service = _service_with_response(response)

    span = MagicMock()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span

    with patch("backend.services.llm_service.tracer", tracer):
        service.generate_gameplay_turn(_story(), _session(), "look")

    tracer.start_as_current_span.assert_called_once_with("gen_ai.gameplay.turn")
    attribute_keys = {call.args[0] for call in span.set_attribute.call_args_list}
    assert attribute_keys == {
        "gen_ai.prompt",
        "gen_ai.response",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.usage.reasoning_tokens",
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


def test_no_unsupported_sampling_parameters_are_sent():
    """gpt-5-nano is a reasoning model: temperature, top_p, the penalties, logprobs,
    logit_bias and max_tokens are rejected outright, and rejected for being present at
    all rather than for their value. Adding one breaks every call, so the option set is
    pinned rather than merely spot-checked."""
    options = _world_prompt_options()

    assert set(options) == {"response_format", "reasoning_effort"}


def test_reasoning_effort_is_never_sent_as_none_for_this_deployment():
    """gpt-5-nano accepts minimal/low/medium/high but not "none", so the opt-out has to
    drop the parameter rather than send that value."""
    assert "none" not in {
        llm_service_module.REASONING_EFFORT_WORLD_PROMPT,
        llm_service_module.REASONING_EFFORT_GENERATION,
        llm_service_module.REASONING_EFFORT_STARTING_POINT,
        llm_service_module.REASONING_EFFORT_GAMEPLAY_TURN,
        llm_service_module.REASONING_EFFORT_GAMEPLAY_SUMMARY,
    }
    assert "reasoning_effort" not in _world_prompt_options(override=llm_service_module.REASONING_EFFORT_OFF)
