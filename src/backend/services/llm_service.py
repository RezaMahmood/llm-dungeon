"""Azure OpenAI LLM client — the one-pass world-prompt suggestion and final
story-generation calls, each wrapped in an OpenTelemetry span carrying full
prompt/response, token counts, computed cost, and latency (Constitution Principle VI;
research.md §1, §2, §4).

Built on the Microsoft Agent Framework's `OpenAIChatCompletionClient` (`agent-framework-openai`)
rather than `azure-ai-inference`, which Microsoft retired on 2026-08-26 — see research.md §1
amendment. Only the plain chat-completion client is used here; no agent/tool/workflow
orchestration from the framework is pulled in (YAGNI)."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

import openai
from agent_framework import Message
from agent_framework.openai import OpenAIChatCompletionClient
from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from backend.config import config
from backend.models.play_session import PlaySession
from backend.models.story import Story
from backend.services.azure_credential import shared_credential

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

# One chat-completion client per endpoint per worker process, so its httpx connection pool
# and that pool's TLS handshake survive between calls.
_clients: dict[str, OpenAIChatCompletionClient] = {}
_clients_lock = threading.Lock()


def _shared_client(endpoint: str) -> OpenAIChatCompletionClient:
    with _clients_lock:
        client = _clients.get(endpoint)
        if client is None:
            client = OpenAIChatCompletionClient(
                model=config.AZURE_AI_FOUNDRY_DEPLOYMENT_NAME,
                azure_endpoint=endpoint,
                credential=shared_credential(),
            )
            _clients[endpoint] = client
        return client


# Sharing the client above requires one long-lived loop: its httpx connection pool is bound
# to the loop that opened it, so an `asyncio.run()` per call eventually reuses a connection
# belonging to a closed loop and raises "RuntimeError: Event loop is closed". A daemon
# thread rather than a lock around one loop, so calls taking seconds still overlap.
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_lock = threading.Lock()


def _shared_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        with _loop_lock:
            if _loop is None or _loop.is_closed():
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name="llm-service-loop", daemon=True).start()
                _loop = loop
    return _loop


def _run(coro: Any) -> Any:
    """Run one client coroutine on the shared loop and block for its result. The exception
    is re-raised unchanged, which `_as_rate_limit_error`'s `__cause__` walk depends on."""
    return asyncio.run_coroutine_threadsafe(coro, _shared_loop()).result()


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8").removesuffix("\n")


WORLD_PROMPT_SYSTEM_PROMPT = _load_prompt("world_prompt_system_prompt.txt")
GENERATION_SYSTEM_PROMPT = _load_prompt("generation_system_prompt.txt")
STARTING_POINT_SYSTEM_PROMPT = _load_prompt("starting_point_system_prompt.txt")
GAMEPLAY_TURN_SYSTEM_PROMPT = _load_prompt("gameplay_turn_system_prompt.txt")
GAMEPLAY_SUMMARY_SYSTEM_PROMPT = _load_prompt("gameplay_summary_system_prompt.txt")

MAX_NARRATIVE_WORDS = 150

# Reasoning effort per call, set against what each call has to work out. The gameplay turn
# judges whether the player's action satisfied a completion condition and that verdict is
# persisted, so it keeps the API's default; the others expand or condense prose. Each is
# individually overridable via its own LLM_REASONING_EFFORT_* app setting (config.py) so a
# single call's latency/quality trade-off can be retuned without a code deploy; the blanket
# LLM_REASONING_EFFORT setting still wins over all of these when set (_resolve_reasoning_effort).
REASONING_EFFORT_WORLD_PROMPT = config.LLM_REASONING_EFFORT_WORLD_PROMPT or "minimal"
REASONING_EFFORT_GENERATION = config.LLM_REASONING_EFFORT_GENERATION or "low"
REASONING_EFFORT_STARTING_POINT = config.LLM_REASONING_EFFORT_STARTING_POINT or "low"
REASONING_EFFORT_GAMEPLAY_TURN = config.LLM_REASONING_EFFORT_GAMEPLAY_TURN or "medium"
REASONING_EFFORT_GAMEPLAY_SUMMARY = config.LLM_REASONING_EFFORT_GAMEPLAY_SUMMARY or "minimal"

# config.LLM_REASONING_EFFORT set to this omits the parameter, for a model that rejects it.
REASONING_EFFORT_OFF = "off"


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
    rejected the prompt or the completion (008-core-gameplay-done research.md Decision 3).
    Callers map this to a safe in-fiction deflection narrative, never a raw error."""


class _WorldPromptResponse(BaseModel):
    """The one-pass world-prompt suggestion's schema (#227) — a single suggested
    `worldPrompt` and nothing else, so the call structurally cannot ask a follow-up
    question or write any other draft field."""

    worldPrompt: str


class _GenerationResponse(BaseModel):
    narrativeGuidance: str


class _StartingPointResponse(BaseModel):
    """The story's fixed opening scene, generated once at story-creation time (#271). No
    session exists yet and no player has acted, so this schema carries no
    completion-condition-matching fields at all."""

    narrativeText: str
    suggestedActions: list[str]
    locationLabel: str
    goalLabel: Optional[str] = None
    progress: Optional[dict[str, int]] = None


class _GameplayTurnResponse(BaseModel):
    narrativeText: str
    suggestedActions: list[str]
    locationLabel: str
    goalLabel: Optional[str] = None
    progress: Optional[dict[str, int]] = None
    newlySatisfiedSuccessConditions: list[int] = []
    newlySatisfiedFailureConditions: list[int] = []


class _SummaryResponse(BaseModel):
    summary: str


class LLMService:
    """Thin wrapper around `agent_framework.openai.OpenAIChatCompletionClient`, authenticated
    via Managed Identity (Constitution Principle VII), matching CosmosService's lazy-client
    construction pattern. `get_response()` is async in the underlying library; each public
    method here dispatches its single call onto the module's shared event loop (`_run`) so
    the rest of the service layer (`story_draft_service.py`, the HTTP handlers) stays
    synchronous, unchanged."""

    def __init__(self, client: Optional[OpenAIChatCompletionClient] = None, endpoint: Optional[str] = None) -> None:
        self._endpoint = endpoint or config.AZURE_AI_FOUNDRY_ENDPOINT
        self._client = client

    @property
    def client(self) -> OpenAIChatCompletionClient:
        if self._client is None:
            self._client = _shared_client(self._endpoint)
        return self._client

    def suggest_world_prompt(self, draft: dict[str, Any], idea: str) -> tuple[str, int]:
        """Turn the administrator's idea into a single suggested world prompt in one pass
        (#227). Deliberately not a conversation: the model is never asked for a follow-up
        question, and exactly one call is made per idea. Returns `(world_prompt,
        tokens_used)` (research.md Decision 1)."""
        prompt = self._build_world_prompt_request(draft, idea)
        result, tokens_used = self._call(
            "gen_ai.story_creation.world_prompt",
            WORLD_PROMPT_SYSTEM_PROMPT,
            prompt,
            _WorldPromptResponse,
            REASONING_EFFORT_WORLD_PROMPT,
        )
        return result.worldPrompt, tokens_used

    def generate_story_config(self, draft: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """Final generation call once the Completeness Rule is met. Returns
        `({"narrativeGuidance": str}, tokens_used)` (research.md §4, Decision 1)."""
        prompt = self._build_generation_prompt(draft)
        result, tokens_used = self._call(
            "gen_ai.story_creation.generate",
            GENERATION_SYSTEM_PROMPT,
            prompt,
            _GenerationResponse,
            REASONING_EFFORT_GENERATION,
        )
        return result.model_dump(), tokens_used

    def generate_starting_point(
        self, draft: dict[str, Any], narrative_guidance: str
    ) -> tuple[dict[str, Any], int]:
        """The story's fixed opening scene, generated once per story from the freshly
        generated `narrative_guidance` and persisted on the `Story` (#271). Turn 0 of every
        session replays it verbatim, so it is deliberately character-agnostic. Returns
        `(data, tokens_used)` (research.md Decision 1)."""
        prompt = self._build_starting_point_prompt(draft, narrative_guidance)
        result, tokens_used = self._call(
            "gen_ai.story_creation.starting_point",
            STARTING_POINT_SYSTEM_PROMPT,
            prompt,
            _StartingPointResponse,
            REASONING_EFFORT_STARTING_POINT,
        )
        data = result.model_dump()
        self._warn_if_over_length(data["narrativeText"])
        return data, tokens_used

    def generate_gameplay_turn(
        self,
        story: Story,
        session: PlaySession,
        player_input: str,
        concluding_reason: Optional[str] = None,
    ) -> tuple[dict[str, Any], int]:
        """One turn of gameplay narrative (008-core-gameplay-done research.md Decision 6).
        Turn 0 never comes from here — it is `story.startingPoint`, replayed verbatim (#271).
        `concluding_reason` asks for an ending; it travels as a narrator directive rather
        than inside `player_input`, which the system prompt instructs the model to distrust
        for behavior changes (FR-012). Returns `(data, tokens_used)` (research.md Decision 1)."""
        prompt = self._build_gameplay_turn_prompt(story, session, player_input, concluding_reason)
        result, tokens_used = self._call(
            "gen_ai.gameplay.turn",
            GAMEPLAY_TURN_SYSTEM_PROMPT,
            prompt,
            _GameplayTurnResponse,
            REASONING_EFFORT_GAMEPLAY_TURN,
        )
        data = result.model_dump()
        self._warn_if_over_length(data["narrativeText"])
        return data, tokens_used

    @staticmethod
    def _warn_if_over_length(narrative_text: str) -> None:
        word_count = len(narrative_text.split())
        if word_count > MAX_NARRATIVE_WORDS:
            # Logged, never truncated (research.md Decision 6a) — truncating mid-sentence
            # could itself introduce a fact-consistency contradiction.
            logger.warning("narrative exceeded %d words (got %d)", MAX_NARRATIVE_WORDS, word_count)

    def summarize_session_history(self, story: Story, session: PlaySession) -> tuple[str, int]:
        """Condenses `session.summary` (if any) plus the turns since
        `session.summarizedThroughTurn` into a fresh summary string (008-core-gameplay-done
        research.md Decision 10, FR-014). May use a different deployment than
        `generate_gameplay_turn` (spec.md Assumptions) — a distinct method/call site is
        what makes that possible. Returns `(summary, tokens_used)` (research.md Decision 1)."""
        prompt = self._build_summary_prompt(story, session)
        result, tokens_used = self._call(
            "gen_ai.gameplay.summary",
            GAMEPLAY_SUMMARY_SYSTEM_PROMPT,
            prompt,
            _SummaryResponse,
            REASONING_EFFORT_GAMEPLAY_SUMMARY,
        )
        return result.summary, tokens_used

    def _call(
        self,
        span_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        reasoning_effort: str,
    ) -> tuple[BaseModel, int]:
        """Returns `(payload, tokens_used)`, where `tokens_used = input_tokens +
        output_tokens` — the same counts the span below already records
        (research.md Decision 1). Reasoning tokens are a subset of output_tokens, not an
        addition to them, matching the existing cost_usd formula."""
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("gen_ai.prompt", user_prompt)
            start = time.monotonic()
            response = self._get_response_with_retry(
                span_name, system_prompt, user_prompt, response_model, reasoning_effort
            )
            latency_ms = (time.monotonic() - start) * 1000

            usage = response.usage_details
            # ChatResponse normalizes usage_details to a plain dict on construction
            # (agent_framework's msgspec-based serialization), not a UsageDetails instance.
            if isinstance(usage, dict):
                input_tokens = usage.get("input_token_count") or 0
                output_tokens = usage.get("output_token_count") or 0
                reasoning_tokens = usage.get("reasoning_output_token_count") or 0
            elif usage is not None:
                input_tokens = getattr(usage, "input_token_count", 0) or 0
                output_tokens = getattr(usage, "output_token_count", 0) or 0
                reasoning_tokens = getattr(usage, "reasoning_output_token_count", 0) or 0
            else:
                input_tokens = output_tokens = reasoning_tokens = 0
            cost_usd = input_tokens * config.LLM_INPUT_TOKEN_PRICE_USD + output_tokens * config.LLM_OUTPUT_TOKEN_PRICE_USD

            span.set_attribute("gen_ai.response", response.text or "")
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
            # A subset of output_tokens, not an addition to them; separates thinking from
            # writing when tuning a call's reasoning effort.
            span.set_attribute("gen_ai.usage.reasoning_tokens", reasoning_tokens)
            span.set_attribute("gen_ai.cost_usd", cost_usd)
            span.set_attribute("gen_ai.latency_ms", latency_ms)

            try:
                return response.value, input_tokens + output_tokens
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                raise LLMOutputError(f"Model response did not match the expected schema: {exc}") from exc

    def _get_response_with_retry(
        self,
        span_name: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        reasoning_effort: str,
    ) -> Any:
        messages = [
            Message(role="system", contents=[system_prompt]),
            Message(role="user", contents=[user_prompt]),
        ]
        # Only these two options. Reasoning models reject temperature, top_p,
        # presence_penalty, frequency_penalty, logprobs, logit_bias and max_tokens — the
        # parameter being present is the error, whatever its value. Cap output with
        # `max_completion_tokens` (which agent_framework renames `max_tokens` to) if ever
        # needed, bearing in mind it truncates mid-JSON rather than shortening the answer.
        options: dict[str, Any] = {"response_format": response_model}
        effort = self._resolve_reasoning_effort(reasoning_effort)
        if effort is not None:
            # Undeclared on agent_framework's chat-completion options, which model only the
            # Responses API's `reasoning` object; unrecognized keys are forwarded to the
            # OpenAI SDK, which accepts `reasoning_effort`.
            options["reasoning_effort"] = effort
        delay = INITIAL_RETRY_DELAY_SECONDS
        for attempt in range(1, MAX_RATE_LIMIT_ATTEMPTS + 1):
            try:
                return _run(self.client.get_response(messages, options=options))
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
    def _resolve_reasoning_effort(call_default: str) -> Optional[str]:
        """The effort to send, or None to omit the parameter."""
        effort = config.LLM_REASONING_EFFORT or call_default
        return None if effort == REASONING_EFFORT_OFF else effort

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

    def _build_world_prompt_request(self, draft: dict[str, Any], idea: str) -> str:
        return "\n".join(["Current draft state:", json.dumps(draft, indent=2), f"\nAdministrator's story idea: {idea}"])

    def _build_generation_prompt(self, draft: dict[str, Any]) -> str:
        return "Complete draft:\n" + json.dumps(draft, indent=2)

    def _build_starting_point_prompt(self, draft: dict[str, Any], narrative_guidance: str) -> str:
        return "\n".join(
            [
                "Complete story configuration:",
                json.dumps(draft, indent=2),
                f"\nNarrative guidance: {narrative_guidance}",
            ]
        )

    def _build_gameplay_turn_prompt(
        self,
        story: Story,
        session: PlaySession,
        player_input: str,
        concluding_reason: Optional[str] = None,
    ) -> str:
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

        lines.append("Prior narrative history:\n" + self._prior_context(session))

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

        if concluding_reason:
            # Kept out of the player-input field on purpose: the system prompt tells the
            # model never to take behaviour changes from player input, so an ending
            # instruction smuggled in there is one it should rightly refuse (FR-012).
            lines.append(
                "Narrator directive (from the game system, not the player): this session is "
                f"ending now because {concluding_reason}. Narrate a scene that brings the "
                "story to a close."
            )

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
