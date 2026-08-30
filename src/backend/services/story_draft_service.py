"""StoryDraftService — draft CRUD, the conversational exchange, field validation, and the
Completeness Rule that triggers automatic generation + persistence (FR-003/FR-004;
data-model.md Story Draft)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.config import config
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.models.story_draft import StoryCreationExchange, StoryDraft
from backend.services.cosmos_service import CosmosService
from backend.services.llm_service import LLMOutputError, LLMService
from backend.services.story_service import StoryService

logger = logging.getLogger("story_draft_service")

# Draft fields settable directly via PATCH or merged from a conversational exchange's
# fieldUpdates (data-model.md Story Draft) — characterTypes/completionCriteria are
# handled separately since they need Shared-Structure validation, not a plain setattr.
PATCHABLE_FIELDS = {
    "name",
    "coverImageUrl",
    "tone",
    "readingLevel",
    "sessionLengthMinutes",
    "chapters",
    "worldPrompt",
    "rules",
}


class DraftValidationError(ValueError):
    """A patched field failed Shared Structure validation — the caller maps this to a 422
    `invalid_field` response; no partial merge happens (contracts/api.md)."""


class GenerationFailedError(RuntimeError):
    """The Completeness Rule was met but the Foundry generation call failed or returned
    invalid output — the caller maps this to 502 `generation_failed`; the draft is left
    unchanged and intact for another attempt (Edge Cases)."""


class StoryDraftService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        llm_service: Optional[LLMService] = None,
        story_service: Optional[StoryService] = None,
    ) -> None:
        self._cosmos = cosmos_service or CosmosService()
        self._llm = llm_service or LLMService()
        self._stories = story_service or StoryService(cosmos_service=self._cosmos)

    def _container(self):
        return self._cosmos.get_container(config.STORY_DRAFTS_CONTAINER)

    def get_draft(self, draft_id: str) -> Optional[StoryDraft]:
        try:
            item = self._container().read_item(item=draft_id, partition_key=draft_id)
        except CosmosResourceNotFoundError:
            return None
        return StoryDraft.from_dict(item)

    def create_draft(self, created_by: str, idea: Optional[str] = None) -> StoryDraft:
        """Start a new session (FR-001), optionally seeded with a plain-language idea
        immediately sent through the guiding-question exchange."""
        draft = StoryDraft(id=str(uuid.uuid4()), createdBy=created_by)
        if idea:
            self._apply_exchange(draft, idea)
        draft.touch()
        self._container().upsert_item(draft.to_dict())
        return draft

    def post_message(self, draft_id: str, message: str) -> tuple[Optional[StoryDraft], Optional[Story]]:
        """Append one administrator message, merge the system's field updates, and
        evaluate the Completeness Rule. Returns `(None, None)` if the draft doesn't exist
        (expired TTL or never existed). Raises `GenerationFailedError` if the Completeness
        Rule was met on this write but generation failed."""
        draft = self.get_draft(draft_id)
        if draft is None:
            return None, None

        self._apply_exchange(draft, message)
        return self._finalize_write(draft)

    def patch_draft(self, draft_id: str, updates: dict[str, Any]) -> tuple[Optional[StoryDraft], Optional[Story]]:
        """Directly edit structured draft fields (FR-008), then evaluate the Completeness
        Rule. Same return/raise contract as `post_message`. Raises `DraftValidationError`
        on the first invalid field — no partial merge."""
        draft = self.get_draft(draft_id)
        if draft is None:
            return None, None

        self._apply_patch(draft, updates)
        return self._finalize_write(draft)

    def _apply_exchange(self, draft: StoryDraft, message: str) -> None:
        draft.exchanges.append(StoryCreationExchange(role="administrator", message=message))
        response = self._llm.generate_exchange_response(draft.to_dict(), message)
        self._merge_field_updates(draft, response.get("fieldUpdates") or {})
        assistant_message = response.get("assistantMessage") or ""
        if assistant_message:
            draft.exchanges.append(StoryCreationExchange(role="system", message=assistant_message))

    def _merge_field_updates(self, draft: StoryDraft, updates: dict[str, Any]) -> None:
        """Merge LLM-extracted field updates — latest write always wins, including over a
        contradictory earlier answer (Edge Cases)."""
        for key, value in updates.items():
            if key in PATCHABLE_FIELDS:
                setattr(draft, key, value)
            elif key == "characterTypes" and isinstance(value, list):
                draft.characterTypes = [CharacterType.from_dict(ct) for ct in value]
            elif key == "completionCriteria" and isinstance(value, dict):
                draft.completionCriteria = CompletionCriteria.from_dict(value)

    def _apply_patch(self, draft: StoryDraft, updates: dict[str, Any]) -> None:
        for field_name in PATCHABLE_FIELDS:
            if field_name in updates:
                setattr(draft, field_name, updates[field_name])

        if "characterTypes" in updates:
            try:
                draft.characterTypes = [CharacterType.from_dict(ct) for ct in updates["characterTypes"]]
            except (ValueError, KeyError, TypeError) as exc:
                raise DraftValidationError(f"characterTypes: {exc}") from exc

        if "completionCriteria" in updates:
            raw = updates["completionCriteria"]
            if raw is None:
                draft.completionCriteria = None
            else:
                try:
                    draft.completionCriteria = CompletionCriteria.from_dict(raw)
                except (ValueError, KeyError, TypeError) as exc:
                    raise DraftValidationError(f"completionCriteria: {exc}") from exc

    def _finalize_write(self, draft: StoryDraft) -> tuple[StoryDraft, Optional[Story]]:
        draft.touch()

        if not draft.is_complete():
            self._container().upsert_item(draft.to_dict())
            return draft, None

        try:
            generation = self._llm.generate_story_config(draft.to_dict())
            narrative_guidance = generation["narrativeGuidance"]
            if not narrative_guidance:
                raise LLMOutputError("narrativeGuidance was empty")
        except LLMOutputError as exc:
            logger.warning("Story generation failed for draft %s: %s", draft.id, exc)
            self._container().upsert_item(draft.to_dict())
            raise GenerationFailedError(str(exc)) from exc

        story = self._stories.create_story(draft, narrative_guidance)
        self._container().delete_item(item=draft.id, partition_key=draft.id)
        return draft, story
