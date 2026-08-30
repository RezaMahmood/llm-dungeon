"""Azure AI Foundry LLM client — the guiding-question exchange and final story-generation
calls, each wrapped in an OpenTelemetry span carrying full prompt/response, token counts,
computed cost, and latency (Constitution Principle VI; research.md §1, §2, §4)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.identity import DefaultAzureCredential
from opentelemetry import trace

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


class LLMService:
    """Thin wrapper around `azure.ai.inference.ChatCompletionsClient`, authenticated via
    Managed Identity (Constitution Principle VII), matching CosmosService's lazy-client
    construction pattern."""

    def __init__(self, client: Optional[ChatCompletionsClient] = None, endpoint: Optional[str] = None) -> None:
        self._endpoint = endpoint or config.AZURE_AI_FOUNDRY_ENDPOINT
        self._client = client

    @property
    def client(self) -> ChatCompletionsClient:
        if self._client is None:
            self._client = ChatCompletionsClient(endpoint=self._endpoint, credential=DefaultAzureCredential())
        return self._client

    def generate_exchange_response(self, draft: dict[str, Any], message: Optional[str]) -> dict[str, Any]:
        """One turn of the guiding-question conversation. Returns
        `{"assistantMessage": str, "fieldUpdates": dict}` (research.md §4)."""
        prompt = self._build_exchange_prompt(draft, message)
        content = self._call("gen_ai.story_creation.exchange", EXCHANGE_SYSTEM_PROMPT, prompt)
        return self._parse_json_response(content, required_keys=("assistantMessage", "fieldUpdates"))

    def generate_story_config(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Final generation call once the Completeness Rule is met. Returns
        `{"narrativeGuidance": str}` (research.md §4)."""
        prompt = self._build_generation_prompt(draft)
        content = self._call("gen_ai.story_creation.generate", GENERATION_SYSTEM_PROMPT, prompt)
        return self._parse_json_response(content, required_keys=("narrativeGuidance",))

    def _call(self, span_name: str, system_prompt: str, user_prompt: str) -> str:
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("gen_ai.prompt", user_prompt)
            start = time.monotonic()
            response = self.client.complete(
                messages=[SystemMessage(content=system_prompt), UserMessage(content=user_prompt)],
                response_format="json_object",
            )
            latency_ms = (time.monotonic() - start) * 1000

            content = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
            cost_usd = input_tokens * config.LLM_INPUT_TOKEN_PRICE_USD + output_tokens * config.LLM_OUTPUT_TOKEN_PRICE_USD

            span.set_attribute("gen_ai.response", content or "")
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
            span.set_attribute("gen_ai.cost_usd", cost_usd)
            span.set_attribute("gen_ai.latency_ms", latency_ms)
            return content

    def _parse_json_response(self, content: Optional[str], required_keys: tuple[str, ...]) -> dict[str, Any]:
        try:
            data = json.loads(content)
        except (TypeError, ValueError) as exc:
            raise LLMOutputError(f"Model response was not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise LLMOutputError("Model response was not a JSON object")

        missing = [key for key in required_keys if key not in data]
        if missing:
            raise LLMOutputError(f"Model response missing required key(s): {missing}")

        return data

    def _build_exchange_prompt(self, draft: dict[str, Any], message: Optional[str]) -> str:
        lines = ["Current draft state:", json.dumps(draft, indent=2)]
        if message:
            lines.append(f"\nAdministrator's latest message: {message}")
        return "\n".join(lines)

    def _build_generation_prompt(self, draft: dict[str, Any]) -> str:
        return "Complete draft:\n" + json.dumps(draft, indent=2)
