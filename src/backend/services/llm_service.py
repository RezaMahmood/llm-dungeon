"""Azure OpenAI LLM client — the guiding-question exchange and final story-generation
calls, each wrapped in an OpenTelemetry span carrying full prompt/response, token counts,
computed cost, and latency (Constitution Principle VI; research.md §1, §2, §4).

Built on the Microsoft Agent Framework's `OpenAIChatCompletionClient` (`agent-framework-openai`)
rather than `azure-ai-inference`, which Microsoft retired on 2026-08-26 — see research.md §1
amendment. Only the plain chat-completion client is used here; no agent/tool/workflow
orchestration from the framework is pulled in (YAGNI)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import openai
from agent_framework import Message
from agent_framework.openai import OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from backend.config import config
from backend.models.play_session import PlaySession
from backend.models.story import Story

logger = logging.getLogger("llm_service")
tracer = trace.get_tracer("backend.services.llm_service")

# The Foundry deployment enforces a requests-per-minute quota; a burst of admin activity
# (e.g. several drafts being worked in parallel) can trip it. Retry with backoff a few
# times before giving up, rather than surfacing the first 429 as an unhandled 500 (#33).
MAX_RATE_LIMIT_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 2.0

# Prompts are kept out of source as plain-text files (#228) so prompt wording can be
# reviewed/diffed/tuned independently of application code; read once at import time
# since Function App instances are short-lived and the files never change at runtime.
_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8").removesuffix("\n")


EXCHANGE_SYSTEM_PROMPT = _load_prompt("exchange_system_prompt.txt")
GENERATION_SYSTEM_PROMPT = _load_prompt("generation_system_prompt.txt")
GAMEPLAY_TURN_SYSTEM_PROMPT = _load_prompt("gameplay_turn_system_prompt.txt")
GAMEPLAY_SUMMARY_SYSTEM_PROMPT = _load_prompt("gameplay_summary_system_prompt.txt")

MAX_NARRATIVE_WORDS = 150


class LLMOutputError(ValueError):
    """Raised when the model's response is not valid JSON, or is missing a required key
    (research.md §4). Callers treat this identically to a failed generation call — the
    triggering write is never partially applied."""


class LLMRateLimitError(RuntimeError):
    """Raised when the Foundry deployment keeps returning HTTP 429 after
    `MAX_RATE_LIMIT_ATTEMPTS` attempts with backoff. Callers treat this like
    `LLMOutputError` — the triggering write is never partially applied — but the caller
    maps it to a distinct, retry-friendly response rather than a generic failure (#33)."""


class LLMContentFilteredError(RuntimeError):
    """Raised when a call fails because the Foundry deployment's default content filter
    rejected the prompt or the completion (008-core-gameplay research.md Decision 3).
    Callers map this to a safe in-fiction deflection narrative, never a raw error."""


class _FieldUpdates(BaseModel):
    """Mirrors the fields listed in `EXCHANGE_SYSTEM_PROMPT`. Declared explicitly (rather
    than `dict[str, Any]`) because Azure OpenAI's structured-output mode requires every
    object in the response schema to have `additionalProperties: false`, which can't be
    inferred for a free-form dict."""

    worldPrompt: Optional[str] = None
    rules: Optional[str] = None
    name: Optional[str] = None
    coverImageUrl: Optional[str] = None
    tone: Optional[str] = None
    readingLevel: Optional[str] = None
    sessionLengthMinutes: Optional[int] = None
    chapters: Optional[int] = None


class _ExchangeResponse(BaseModel):
    assistantMessage: str
    fieldUpdates: _FieldUpdates = _FieldUpdates()


class _GenerationResponse(BaseModel):
    narrativeGuidance: str


class _OpeningNarrativeResponse(BaseModel):
    """The turn-0 (opening-narrative) call's schema — no player input yet exists, so a
    session cannot end before the player has acted (research.md Decision 6): this schema
    has no completion-condition-matching fields at all."""

    narrativeText: str
    suggestedActions: list[str]
    locationLabel: str
    goalLabel: Optional[str] = None
    progress: Optional[dict[str, int]] = None


class _GameplayTurnResponse(_OpeningNarrativeResponse):
    newlySatisfiedSuccessConditions: list[int] = []
    newlySatisfiedFailureConditions: list[int] = []


class _SummaryResponse(BaseModel):
    summary: str


class LLMService:
    """Thin wrapper around `agent_framework.openai.OpenAIChatCompletionClient`, authenticated
    via Managed Identity (Constitution Principle VII), matching CosmosService's lazy-client
    construction pattern. `get_response()` is async in the underlying library; each public
    method here runs its single call via `asyncio.run()` so the rest of the service layer
    (`story_draft_service.py`, the HTTP handlers) stays synchronous, unchanged."""

    def __init__(self, client: Optional[OpenAIChatCompletionClient] = None, endpoint: Optional[str] = None) -> None:
        self._endpoint = endpoint or config.AZURE_AI_FOUNDRY_ENDPOINT
        self._client = client

    @property
    def client(self) -> OpenAIChatCompletionClient:
        if self._client is None:
            self._client = OpenAIChatCompletionClient(
                model=config.AZURE_AI_FOUNDRY_DEPLOYMENT_NAME,
                azure_endpoint=self._endpoint,
                credential=DefaultAzureCredential(),
            )
        return self._client

    def generate_exchange_response(self, draft: dict[str, Any], message: Optional[str]) -> dict[str, Any]:
        """One turn of the guiding-question conversation. Returns
        `{"assistantMessage": str, "fieldUpdates": dict}` (research.md §4)."""
        prompt = self._build_exchange_prompt(draft, message)
        result = self._call("gen_ai.story_creation.exchange", EXCHANGE_SYSTEM_PROMPT, prompt, _ExchangeResponse)
        return result.model_dump(exclude_none=True)

    def generate_story_config(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Final generation call once the Completeness Rule is met. Returns
        `{"narrativeGuidance": str}` (research.md §4)."""
        prompt = self._build_generation_prompt(draft)
        result = self._call("gen_ai.story_creation.generate", GENERATION_SYSTEM_PROMPT, prompt, _GenerationResponse)
        return result.model_dump()

    def generate_gameplay_turn(self, story: Story, session: PlaySession, player_input: Optional[str]) -> dict[str, Any]:
        """One turn of gameplay narrative (008-core-gameplay research.md Decision 6).
        `player_input is None` is the opening-narrative call (turn 0), which skips
        requesting completion-condition matching entirely — a session cannot end before
        the player has acted."""
        prompt = self._build_gameplay_turn_prompt(story, session, player_input)
        response_model = _OpeningNarrativeResponse if player_input is None else _GameplayTurnResponse
        result = self._call("gen_ai.gameplay.turn", GAMEPLAY_TURN_SYSTEM_PROMPT, prompt, response_model)
        data = result.model_dump()
        data.setdefault("newlySatisfiedSuccessConditions", [])
        data.setdefault("newlySatisfiedFailureConditions", [])

        word_count = len(data["narrativeText"].split())
        if word_count > MAX_NARRATIVE_WORDS:
            # Logged, never truncated (research.md Decision 6a) — truncating mid-sentence
            # could itself introduce a fact-consistency contradiction.
            logger.warning("gameplay turn narrative exceeded %d words (got %d)", MAX_NARRATIVE_WORDS, word_count)
        return data

    def summarize_session_history(self, story: Story, session: PlaySession) -> str:
        """Condenses `session.summary` (if any) plus the turns since
        `session.summarizedThroughTurn` into a fresh summary string (008-core-gameplay
        research.md Decision 10, FR-014). May use a different deployment than
        `generate_gameplay_turn` (spec.md Assumptions) — a distinct method/call site is
        what makes that possible."""
        prompt = self._build_summary_prompt(story, session)
        result = self._call("gen_ai.gameplay.summary", GAMEPLAY_SUMMARY_SYSTEM_PROMPT, prompt, _SummaryResponse)
        return result.summary

    def _call(
        self,
        span_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> BaseModel:
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("gen_ai.prompt", user_prompt)
            start = time.monotonic()
            response = self._get_response_with_retry(span_name, system_prompt, user_prompt, response_model)
            latency_ms = (time.monotonic() - start) * 1000

            usage = response.usage_details
            # ChatResponse normalizes usage_details to a plain dict on construction
            # (agent_framework's msgspec-based serialization), not a UsageDetails instance.
            if isinstance(usage, dict):
                input_tokens = usage.get("input_token_count") or 0
                output_tokens = usage.get("output_token_count") or 0
            elif usage is not None:
                input_tokens = getattr(usage, "input_token_count", 0) or 0
                output_tokens = getattr(usage, "output_token_count", 0) or 0
            else:
                input_tokens = output_tokens = 0
            cost_usd = input_tokens * config.LLM_INPUT_TOKEN_PRICE_USD + output_tokens * config.LLM_OUTPUT_TOKEN_PRICE_USD

            span.set_attribute("gen_ai.response", response.text or "")
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
            span.set_attribute("gen_ai.cost_usd", cost_usd)
            span.set_attribute("gen_ai.latency_ms", latency_ms)

            try:
                return response.value
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                raise LLMOutputError(f"Model response did not match the expected schema: {exc}") from exc

    def _get_response_with_retry(
        self,
        span_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> Any:
        messages = [
            Message(role="system", contents=[system_prompt]),
            Message(role="user", contents=[user_prompt]),
        ]
        delay = INITIAL_RETRY_DELAY_SECONDS
        for attempt in range(1, MAX_RATE_LIMIT_ATTEMPTS + 1):
            try:
                return asyncio.run(
                    self.client.get_response(messages, options={"response_format": response_model})
                )
            except Exception as exc:  # noqa: BLE001 - re-raised untouched unless it's a 429/content-filter
                rate_limit_error = self._as_rate_limit_error(exc)
                if rate_limit_error is None:
                    if self._as_content_filter_error(exc) is not None:
                        raise LLMContentFilteredError(f"{span_name} was blocked by content filtering") from exc
                    raise
                if attempt == MAX_RATE_LIMIT_ATTEMPTS:
                    raise LLMRateLimitError(
                        f"{span_name} was rate-limited on all {MAX_RATE_LIMIT_ATTEMPTS} attempts"
                    ) from exc
                wait_seconds = self._retry_after_seconds(rate_limit_error, fallback=delay)
                logger.warning(
                    "%s rate-limited (attempt %d/%d); retrying in %.1fs",
                    span_name,
                    attempt,
                    MAX_RATE_LIMIT_ATTEMPTS,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                delay *= 2
        raise AssertionError("unreachable: loop always returns or raises")

    @staticmethod
    def _as_rate_limit_error(exc: Exception) -> Optional[openai.RateLimitError]:
        """Unwraps `agent_framework`'s `ChatClientException` (or any other wrapper) to find
        the underlying `openai.RateLimitError`, if the failure was in fact a 429."""
        seen: set[int] = set()
        current: Optional[BaseException] = exc
        while current is not None and id(current) not in seen:
            if isinstance(current, openai.RateLimitError):
                return current
            seen.add(id(current))
            current = current.__cause__
        return None

    @staticmethod
    def _as_content_filter_error(exc: Exception) -> Optional[openai.BadRequestError]:
        """Unwraps to find an underlying `openai.BadRequestError` whose code/body indicates
        the Foundry deployment's default content filter rejected the prompt or completion
        (research.md Decision 3)."""
        seen: set[int] = set()
        current: Optional[BaseException] = exc
        while current is not None and id(current) not in seen:
            if isinstance(current, openai.BadRequestError):
                body = getattr(current, "body", None) or {}
                nested_error = body.get("error") if isinstance(body, dict) else None
                codes = [
                    getattr(current, "code", None),
                    body.get("code") if isinstance(body, dict) else None,
                    nested_error.get("code") if isinstance(nested_error, dict) else None,
                ]
                if any(code and "content_filter" in str(code) for code in codes):
                    return current
            seen.add(id(current))
            current = current.__cause__
        return None

    @staticmethod
    def _retry_after_seconds(exc: openai.RateLimitError, fallback: float) -> float:
        response = getattr(exc, "response", None)
        header = response.headers.get("retry-after") if response is not None else None
        if header:
            try:
                return max(float(header), 0.0)
            except ValueError:
                pass
        return fallback

    def _build_exchange_prompt(self, draft: dict[str, Any], message: Optional[str]) -> str:
        lines = ["Current draft state:", json.dumps(draft, indent=2)]
        if message:
            lines.append(f"\nAdministrator's latest message: {message}")
        return "\n".join(lines)

    def _build_generation_prompt(self, draft: dict[str, Any]) -> str:
        return "Complete draft:\n" + json.dumps(draft, indent=2)

    def _build_gameplay_turn_prompt(self, story: Story, session: PlaySession, player_input: Optional[str]) -> str:
        lines = [f"World: {story.worldPrompt}"]
        if story.rules:
            lines.append(f"Rules: {story.rules}")
        if story.narrativeGuidance:
            lines.append(f"Narrative guidance: {story.narrativeGuidance}")
        if story.tone:
            lines.append(f"Tone: {story.tone}")
        if story.readingLevel:
            lines.append(f"Reading level: {story.readingLevel}")
        if story.chapters:
            lines.append(f"Total chapters: {story.chapters}")
        lines.append(f"Character: {session.characterName} ({session.characterType})")

        history = self._prior_context(session)
        lines.append("Prior narrative history:\n" + history if history else "This is the opening turn — no prior history yet.")

        if player_input is not None:
            criteria = story.completionCriteria
            remaining_success = [
                (i, text)
                for i, text in enumerate(criteria.successConditions)
                if i not in session.satisfiedSuccessConditions
            ]
            remaining_failure = [
                (i, text)
                for i, text in enumerate(criteria.failureConditions)
                if i not in session.satisfiedFailureConditions
            ]
            if remaining_success:
                lines.append(
                    "Not-yet-satisfied success conditions (index: text):\n"
                    + "\n".join(f"  {i}: {text}" for i, text in remaining_success)
                )
            if remaining_failure:
                lines.append(
                    "Not-yet-satisfied failure conditions (index: text):\n"
                    + "\n".join(f"  {i}: {text}" for i, text in remaining_failure)
                )
            lines.append(f"Player's latest input: {player_input}")
        else:
            lines.append("Generate the opening narrative for this session's first turn.")

        return "\n\n".join(lines)

    def _build_summary_prompt(self, story: Story, session: PlaySession) -> str:
        lines = [f"World: {story.worldPrompt}"]
        if session.summary:
            lines.append(f"Prior summary: {session.summary}")
        for turn in session.turns:
            if turn.turnNumber <= session.summarizedThroughTurn:
                continue
            if turn.playerInput is not None:
                lines.append(f"Turn {turn.turnNumber} — player: {turn.playerInput}")
            lines.append(f"Turn {turn.turnNumber} — narrative: {turn.narrativeText}")
        return "\n".join(lines)

    def _prior_context(self, session: PlaySession) -> str:
        """Prior narrative context for a turn call: `summary` + only turns after
        `summarizedThroughTurn` once a summary exists, else the full `turns` history
        (research.md Decision 10)."""
        lines: list[str] = []
        if session.summary:
            lines.append(f"Summary so far: {session.summary}")
        for turn in session.turns:
            if session.summary and turn.turnNumber <= session.summarizedThroughTurn:
                continue
            if turn.playerInput is not None:
                lines.append(f"Turn {turn.turnNumber} — player: {turn.playerInput}")
            lines.append(f"Turn {turn.turnNumber} — narrative: {turn.narrativeText}")
        return "\n".join(lines)
