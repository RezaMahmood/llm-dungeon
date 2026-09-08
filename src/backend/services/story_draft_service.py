"""StoryDraftService — draft CRUD, the one-pass world-prompt suggestion, field
validation, and the explicit generation step that turns a complete draft into a persisted
Story (FR-003/FR-004; data-model.md Story Draft). Generation is a separate,
administrator-triggered action (`generate_story`) — it is never a side effect of a field
write, so filling in the last required field never itself navigates the administrator
away (#33 follow-up)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.config import config
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.models.story_draft import StoryDraft
from backend.services.cosmos_service import CosmosService
from backend.services.llm_service import LLMOutputError, LLMRateLimitError, LLMService
from backend.services.story_config_file import StoryConfiguration
from backend.services.story_service import StaleStoryError, StoryService

logger = logging.getLogger("story_draft_service")

# Draft fields settable directly via PATCH (data-model.md Story Draft) —
# characterTypes/completionCriteria are handled separately since they need
# Shared-Structure validation, not a plain setattr.
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
    """The Foundry generation call failed or returned invalid output — the caller maps
    this to 502 `generation_failed`; the draft is left unchanged and intact for another
    attempt (Edge Cases)."""


class LLMRateLimitedError(RuntimeError):
    """The Foundry deployment rate-limited a world-prompt suggestion or generation call
    after retries were exhausted — the caller maps this to 429 `rate_limited`; the draft
    is left unchanged and intact for another attempt (#33)."""


class DraftIncompleteError(ValueError):
    """`generate_story` was called before the Completeness Rule was met — the caller maps
    this to a 422 `not_ready` response."""


class WrongDraftModeError(ValueError):
    """A creation draft was posted to the save endpoint, or an edit draft was posted to
    `generate_story` (data-model.md → Mode rules) — the caller maps this to a 422
    `wrong_draft_mode` response."""


class DraftNotFoundError(ValueError):
    """`save_draft_to_story` was called for a draft, or a source story, that no longer
    exists — the caller distinguishes which via the message and maps both to 404."""


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
        immediately turned into a suggested world prompt. A blank or whitespace-only
        `idea` starts a blank draft rather than spending a Foundry call on nothing."""
        draft = StoryDraft(id=str(uuid.uuid4()), createdBy=created_by)
        idea = (idea or "").strip()
        if idea:
            self._apply_world_prompt_suggestion(draft, idea)
        draft.touch()
        self._container().upsert_item(draft.to_dict())
        return draft

    def suggest_world_prompt(self, draft_id: str, idea: str) -> Optional[StoryDraft]:
        """Send the administrator's idea to the model exactly once and store what comes
        back as the draft's `worldPrompt` (#227) — a single pass, not a conversation, and
        nothing but `worldPrompt` is written. Returns `None` if the draft doesn't exist
        (expired TTL or never existed). Never generates a Story — the administrator
        triggers that explicitly via `generate_story` once the Completeness Rule is met,
        so asking for a suggestion never itself navigates them away (#33). Raises
        `DraftValidationError` for a blank or whitespace-only idea — rejected before the
        Foundry call, so an empty request can neither spend tokens nor overwrite a
        `worldPrompt` the administrator already has."""
        idea = (idea or "").strip()
        if not idea:
            raise DraftValidationError("idea: describe your story idea before asking for a world prompt")

        draft = self.get_draft(draft_id)
        if draft is None:
            return None

        self._apply_world_prompt_suggestion(draft, idea)
        draft.touch()
        self._container().upsert_item(draft.to_dict())
        return draft

    def patch_draft(self, draft_id: str, updates: dict[str, Any]) -> Optional[StoryDraft]:
        """Directly edit structured draft fields (FR-008). Same return contract as
        `suggest_world_prompt`. Raises `DraftValidationError` on the first invalid field —
        no partial merge. Never generates a Story (see `suggest_world_prompt`)."""
        draft = self.get_draft(draft_id)
        if draft is None:
            return None

        self._apply_patch(draft, updates)
        draft.touch()
        self._container().upsert_item(draft.to_dict())
        return draft

    def create_edit_draft(self, story: Story, created_by: str) -> StoryDraft:
        """Reopen `story` in the wizard (FR-003) by seeding a `StoryDraft` from its current
        authored fields, bound to it by `sourceStoryId` and pinned to the `contentVersion`
        it was seeded from (data-model.md → StoryDraft)."""
        draft = StoryDraft(
            id=str(uuid.uuid4()),
            createdBy=created_by,
            name=story.name,
            coverImageUrl=story.coverImageUrl,
            tone=story.tone,
            readingLevel=story.readingLevel,
            sessionLengthMinutes=story.sessionLengthMinutes,
            chapters=story.chapters,
            worldPrompt=story.worldPrompt,
            rules=story.rules,
            characterTypes=story.characterTypes,
            completionCriteria=story.completionCriteria,
            sourceStoryId=story.id,
            baseContentVersion=story.contentVersion,
        )
        self._container().upsert_item(draft.to_dict())
        return draft

    def save_draft_to_story(self, draft_id: str, admin_oid: str) -> Optional[Story]:
        """Edit mode's terminal action (contracts/api.md → POST …/drafts/{draftId}/save):
        apply an edit draft back to its source story and delete the draft. Returns `None`
        if the draft doesn't exist. Raises `WrongDraftModeError` for a creation draft,
        `DraftIncompleteError` if the Completeness Rule isn't met, `DraftNotFoundError` if
        the source story is gone, `StaleStoryError` if the story changed since the draft
        was seeded (the draft is left intact), and `ContentGenerationFailedError`/
        `ContentGenerationRateLimitedError` if narrativeGuidance regeneration fails (the
        story is left unchanged in every failure case)."""
        draft = self.get_draft(draft_id)
        if draft is None:
            return None

        if draft.sourceStoryId is None:
            raise WrongDraftModeError("This draft is not an edit of an existing story")

        if not draft.is_complete():
            raise DraftIncompleteError("name, worldPrompt, characterTypes, and completionCriteria are all required before saving")

        story = self._stories.get_story(draft.sourceStoryId)
        if story is None:
            raise DraftNotFoundError("Story not found")

        if draft.baseContentVersion != story.contentVersion:
            raise StaleStoryError()

        configuration = StoryConfiguration(
            id=story.id,
            name=draft.name,
            coverImageUrl=draft.coverImageUrl,
            tone=draft.tone,
            readingLevel=draft.readingLevel,
            sessionLengthMinutes=draft.sessionLengthMinutes,
            chapters=draft.chapters,
            worldPrompt=draft.worldPrompt,
            rules=draft.rules,
            characterTypes=draft.characterTypes,
            completionCriteria=draft.completionCriteria,
        )
        narrative_guidance = self._stories.regenerate_narrative_guidance(configuration, draft.name)
        updated = self._stories.apply_content_write(story, configuration, admin_oid, narrative_guidance)
        self._container().delete_item(item=draft.id, partition_key=draft.id)
        return updated

    def generate_story(self, draft_id: str) -> Optional[Story]:
        """The administrator's explicit "finish" action: generate the story's narrative
        guidance and persist a complete `Story`, deleting the draft. Returns `None` if the
        draft doesn't exist. Raises `WrongDraftModeError` if the draft is an edit of an
        existing story (data-model.md → Mode rules — an edit must never mint a second
        story), `DraftIncompleteError` if the Completeness Rule isn't met yet,
        `GenerationFailedError`/`LLMRateLimitedError` if the Foundry call fails — in both
        failure cases the draft is left unchanged and intact for another attempt."""
        draft = self.get_draft(draft_id)
        if draft is None:
            return None

        if draft.sourceStoryId is not None:
            raise WrongDraftModeError("This draft is an edit of an existing story")

        if not draft.is_complete():
            raise DraftIncompleteError("name, worldPrompt, characterTypes, and completionCriteria are all required")

        try:
            generation = self._llm.generate_story_config(draft.to_dict())
            narrative_guidance = generation["narrativeGuidance"]
            if not narrative_guidance:
                raise LLMOutputError("narrativeGuidance was empty")
        except LLMRateLimitError as exc:
            logger.warning("Story generation rate-limited for draft %s: %s", draft.id, exc)
            raise LLMRateLimitedError(str(exc)) from exc
        except LLMOutputError as exc:
            logger.warning("Story generation failed for draft %s: %s", draft.id, exc)
            raise GenerationFailedError(str(exc)) from exc

        story = self._stories.create_story(draft, narrative_guidance)
        self._container().delete_item(item=draft.id, partition_key=draft.id)
        return story

    def _apply_world_prompt_suggestion(self, draft: StoryDraft, idea: str) -> None:
        """The latest suggestion always wins over whatever `worldPrompt` held before
        (Edge Cases); an empty suggestion is discarded rather than blanking the field."""
        try:
            world_prompt = self._llm.suggest_world_prompt(draft.to_dict(), idea)
        except LLMRateLimitError as exc:
            raise LLMRateLimitedError(str(exc)) from exc
        if world_prompt:
            draft.worldPrompt = world_prompt

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
