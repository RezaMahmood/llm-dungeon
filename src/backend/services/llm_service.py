"""Azure OpenAI LLM client — Tab 02's one-shot outline "Suggest" call (FR-003), wrapped in
an OpenTelemetry span carrying full prompt/response, token counts, computed cost, and
latency (Constitution Principle VI; research.md §1, §2, §4).

Built on the Microsoft Agent Framework's `OpenAIChatCompletionClient` (`agent-framework-openai`)
rather than `azure-ai-inference`, which Microsoft retired on 2026-08-26 — see research.md §1
amendment. Only the plain chat-completion client is used here; no agent/tool/workflow
orchestration from the framework is pulled in (YAGNI).

This service previously also drove a multi-turn guiding-question exchange
(`generate_exchange_response`) that fed the old auto-generation design. That flow was
removed by the Session 2026-08-30 redesign (FR-003: Tab 02's Suggest action is a single,
one-shot generation, not an ongoing chat) — `suggest_outline()` is the only LLM call this
feature makes now."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from agent_framework import Message
from agent_framework.openai import OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from backend.config import config

logger = logging.getLogger("llm_service")
tracer = trace.get_tracer("backend.services.llm_service")

SUGGEST_OUTLINE_SYSTEM_PROMPT = """You are helping an administrator draft the setting/plot \
outline for a new story in a text-adventure game aimed at young players. Given the \
administrator's idea or guiding question, respond with a single JSON object of exactly \
this shape:

{"outline": "<a suggested story outline — setting, premise, and plot arc, written in \
plain prose the administrator can edit>"}

This is a single, one-shot suggestion — do not ask a follow-up question, do not address \
the administrator directly, and never invent character types or completion criteria \
(those are collected through dedicated form fields elsewhere). Respond with JSON only, no \
surrounding prose."""


class LLMOutputError(ValueError):
    """Raised when the model's response is not valid JSON, or is missing a required key
    (research.md §4). The caller surfaces this to the administrator without touching the
    existing outline text box contents (Edge Cases)."""


class _OutlineResponse(BaseModel):
    outline: str


class LLMService:
    """Thin wrapper around `agent_framework.openai.OpenAIChatCompletionClient`, authenticated
    via Managed Identity (Constitution Principle VII), matching CosmosService's lazy-client
    construction pattern. `get_response()` is async in the underlying library; each public
    method here runs its single call via `asyncio.run()` so the rest of the service layer
    stays synchronous."""

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

    def suggest_outline(self, idea: str) -> str:
        """Tab 02's one-shot "Suggest" action (FR-003). Given an administrator's idea or
        guiding question, returns a suggested outline string to inject into the editable
        outline text box. Raises `LLMOutputError` on a malformed/empty model response."""
        prompt = f"Administrator's idea or guiding question:\n{idea}"
        result = self._call("gen_ai.story_creation.suggest_outline", SUGGEST_OUTLINE_SYSTEM_PROMPT, prompt, _OutlineResponse)
        outline = result.outline
        if not outline:
            raise LLMOutputError("Model returned an empty outline")
        return outline

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
