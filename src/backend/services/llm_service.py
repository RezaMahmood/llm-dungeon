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
from typing import Any, Optional

from agent_framework import Message
from agent_framework.openai import OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from backend.config import config

logger = logging.getLogger("llm_service")
tracer = trace.get_tracer("backend.services.llm_service")

EXCHANGE_SYSTEM_PROMPT = """You are helping an administrator create a new story for a \
text-adventure game aimed at young players, through a guided conversation. Read the \
current draft state and the administrator's latest message (if any), then respond with a \
single JSON object of exactly this shape:

{"assistantMessage": "<your next guiding question or acknowledgment>", \
"fieldUpdates": {"worldPrompt": "<string or omit>", "rules": "<string or omit>", \
"name": "<string or omit>", "coverImageUrl": "<string or omit>", "tone": "<string or omit>", \
"readingLevel": "<string or omit>", "sessionLengthMinutes": <integer or omit>, \
"chapters": <integer or omit>}}

Only include a field in fieldUpdates when the conversation actually established or changed \
its value; omit fields you have no new information for. Focus your guiding questions on \
setting/plot detail not yet captured in worldPrompt. Never invent characterTypes or \
completionCriteria — those are collected through dedicated form fields, not this \
conversation. Respond with JSON only, no surrounding prose."""

GENERATION_SYSTEM_PROMPT = """You are generating the final narrative-consistency guidance \
for a complete story configuration in a text-adventure game for young players. Read the \
complete draft below and respond with a single JSON object of exactly this shape:

{"narrativeGuidance": "<prose guidance the game's narrator will follow to keep every \
session consistent with this story's setting, characters, and rules>"}

The guidance must be specific to the supplied worldPrompt, rules, characterTypes, and \
completionCriteria — never generic. Respond with JSON only, no surrounding prose."""


class LLMOutputError(ValueError):
    """Raised when the model's response is not valid JSON, or is missing a required key
    (research.md §4). Callers treat this identically to a failed generation call — the
    triggering write is never partially applied."""


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
            response = asyncio.run(
                self.client.get_response(
                    [
                        Message(role="system", contents=[system_prompt]),
                        Message(role="user", contents=[user_prompt]),
                    ],
                    options={"response_format": response_model},
                )
            )
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

    def _build_exchange_prompt(self, draft: dict[str, Any], message: Optional[str]) -> str:
        lines = ["Current draft state:", json.dumps(draft, indent=2)]
        if message:
            lines.append(f"\nAdministrator's latest message: {message}")
        return "\n".join(lines)

    def _build_generation_prompt(self, draft: dict[str, Any]) -> str:
        return "Complete draft:\n" + json.dumps(draft, indent=2)
