"""StoryService — persist a generated Story, fetch one by id, list summaries."""

from __future__ import annotations

import datetime
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Union

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.models.story import ADMIN_EDITABLE_DERIVED_FIELDS, StartingPoint, Story
from backend.models.story_draft import StoryDraft
from backend.services.cosmos_service import CosmosService
from backend.services.llm_service import (
    LLMContentFilteredError,
    LLMOutputError,
    LLMRateLimitError,
    LLMService,
)
from backend.services.story_config_file import StoryConfiguration

logger = logging.getLogger("story_service")


class StaleStoryError(RuntimeError):
    """FR-006: a content write was attempted against a `Story` whose `contentVersion` has
    since moved on. The caller maps this to `409 stale_story`; nothing is written."""


class WriteConflictError(RuntimeError):
    """A concurrent write won the Cosmos `_etag` precondition race twice in a row
    (contracts/api.md → Write conflicts). The caller maps this to `409 write_conflict`;
    nothing is written."""


class StoryNotFoundError(RuntimeError):
    """The import endpoint's file `id` matches no existing story (research.md §7's routing
    table). The caller maps this to `404 story_not_found`."""


class ContentGenerationFailedError(RuntimeError):
    """`narrativeGuidance`/`startingPoint` (re)generation (research.md §5, #271) failed or
    returned invalid output on a content write. The caller maps this to
    `502 generation_failed`; the story is left unchanged."""


class ContentGenerationRateLimitedError(RuntimeError):
    """`narrativeGuidance`/`startingPoint` (re)generation was rate-limited after retries
    were exhausted. The caller maps this to `429 rate_limited`; the story is left
    unchanged."""


class ConfirmationRequiredError(RuntimeError):
    """An id-carrying import was posted without a matching `confirmOverwriteStoryId`
    (`011` FR-006). The caller maps this to `422 confirmation_required`."""


class TitleRequiredError(RuntimeError):
    """An id-less import was posted without a `title` (`011` FR-005). The caller maps this
    to `422 title_required`."""


class _PublishGateNotSatisfied:
    """Sentinel type returned by `StoryService.publish` when the FR-008 gate blocks the
    publish; the API layer maps an instance of this to a 409 response."""

    def __repr__(self) -> str:
        return "PUBLISH_GATE_NOT_SATISFIED"


PUBLISH_GATE_NOT_SATISFIED = _PublishGateNotSatisfied()


@dataclass(frozen=True)
class DerivedContent:
    """What a content write persists for the two LLM-generated fields, and which of them
    the administrator wrote themselves (`Story.adminEditedFields`)."""

    narrativeGuidance: str
    startingPoint: StartingPoint
    adminEditedFields: list[str]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StoryService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        self._cosmos = cosmos_service or CosmosService()
        self._llm = llm_service or LLMService()

    def _container(self):
        return self._cosmos.get_container(config.STORIES_CONTAINER)

    def _read_item(self, story_id: str) -> Optional[dict[str, Any]]:
        try:
            return self._container().read_item(item=story_id, partition_key=story_id)
        except CosmosResourceNotFoundError:
            return None

    def derived_content(
        self, configuration: StoryConfiguration, name: Optional[str], existing: Optional[Story] = None
    ) -> DerivedContent:
        """The `narrativeGuidance` and `startingPoint` a content write persists. A value
        the configuration file itself supplies is kept verbatim — both are authored,
        admin-editable content (#270, #271); anything absent is generated from the
        authored fields, `startingPoint` from the guidance that goes with it. `name` is
        passed separately because a new-story import's `title` may differ from the file's
        own `name`; `existing` is the story being overwritten, against which a supplied
        value is judged hand-edited or not."""
        draft_like = self._draft_like(configuration, name)
        admin_edited: list[str] = []

        narrative_guidance = configuration.narrativeGuidance
        if narrative_guidance:
            if self._is_admin_edited("narrativeGuidance", narrative_guidance, existing):
                admin_edited.append("narrativeGuidance")
        else:
            narrative_guidance = self._generate_narrative_guidance(draft_like)

        starting_point = configuration.startingPoint
        if starting_point:
            if self._is_admin_edited("startingPoint", starting_point, existing):
                admin_edited.append("startingPoint")
        else:
            starting_point = self._generate_starting_point(draft_like, narrative_guidance)

        return DerivedContent(narrative_guidance, starting_point, admin_edited)

    @staticmethod
    def _is_admin_edited(field_name: str, supplied: Any, existing: Optional[Story]) -> bool:
        """A supplied value is the administrator's own from the moment it differs from what
        the story already holds, and stays theirs on a later write that resubmits it
        unchanged — so an untouched download/upload round-trip of a generated value does not
        freeze it (user review, PR #279)."""
        if existing is None:
            return True
        return supplied != getattr(existing, field_name) or field_name in existing.adminEditedFields

    def carry_admin_edits(self, story: Story, configuration: StoryConfiguration) -> None:
        """Seed a configuration built without the derived fields — a wizard edit draft
        carries neither — with the ones this story's administrator wrote by hand, so the
        save preserves them instead of regenerating over them (user review, PR #279)."""
        for field_name in ADMIN_EDITABLE_DERIVED_FIELDS:
            if field_name in story.adminEditedFields:
                setattr(configuration, field_name, getattr(story, field_name))

    @staticmethod
    def _draft_like(source: Union[StoryConfiguration, Story], name: Optional[str]) -> dict[str, Any]:
        """The generation calls' input shape, from either an uploaded configuration or an
        already-persisted story — the two carry the same authored fields."""
        return {
            "name": name,
            "coverImageUrl": source.coverImageUrl,
            "tone": source.tone,
            "readingLevel": source.readingLevel,
            "sessionLengthMinutes": source.sessionLengthMinutes,
            "chapters": source.chapters,
            "worldPrompt": source.worldPrompt,
            "rules": source.rules,
            "characterTypes": [ct.to_dict() for ct in source.characterTypes],
            "completionCriteria": source.completionCriteria.to_dict(),
        }

    def _generate_narrative_guidance(self, draft_like: dict[str, Any]) -> str:
        """Reuses the creation path's generation call (research.md §5)."""
        try:
            generation = self._llm.generate_story_config(draft_like)
            narrative_guidance = generation["narrativeGuidance"]
            if not narrative_guidance:
                raise LLMOutputError("narrativeGuidance was empty")
        except LLMRateLimitError as exc:
            raise ContentGenerationRateLimitedError(str(exc)) from exc
        except (LLMOutputError, LLMContentFilteredError) as exc:
            raise ContentGenerationFailedError(str(exc)) from exc
        return narrative_guidance

    def _generate_starting_point(self, draft_like: dict[str, Any], narrative_guidance: str) -> StartingPoint:
        try:
            return StartingPoint.from_dict(self._llm.generate_starting_point(draft_like, narrative_guidance))
        except LLMRateLimitError as exc:
            raise ContentGenerationRateLimitedError(str(exc)) from exc
        except (LLMOutputError, LLMContentFilteredError, ValueError, KeyError) as exc:
            # A content-filtered generation is a failed generation like any other here —
            # the admin write paths map it to 502, never an unhandled 500.
            raise ContentGenerationFailedError(str(exc)) from exc

    def ensure_starting_point(self, story: Story) -> Story:
        """Backfill for a `Story` persisted before `startingPoint` existed (#271): generate
        one from the story's own content and write it back, so this costs one LLM call for
        that story's first session and none thereafter. A lost `_etag` race adopts the
        winner's opening, so concurrent first sessions still converge on one turn 0."""
        if story.startingPoint:
            return story

        draft_like = self._draft_like(story, story.name)
        story.startingPoint = self._generate_starting_point(draft_like, story.narrativeGuidance)

        item = self._read_item(story.id)
        if item is None:
            raise StoryNotFoundError()
        persisted = Story.from_dict(item)
        if persisted.startingPoint:
            story.startingPoint = persisted.startingPoint
            return story
        persisted.startingPoint = story.startingPoint
        try:
            self._container().replace_item(
                item=persisted.id,
                body=persisted.to_dict(),
                etag=item["_etag"],
                match_condition=MatchConditions.IfNotModified,
            )
        except CosmosAccessConditionFailedError:
            logger.warning("Starting-point backfill lost an etag race", extra={"story_id": story.id})
            winner = self._read_item(story.id)
            if winner and winner.get("startingPoint"):
                story.startingPoint = StartingPoint.from_dict(winner["startingPoint"])
        return story

    def create_story(self, draft: StoryDraft, narrative_guidance: str, starting_point: StartingPoint) -> Story:
        """Persist a complete `Story` from a draft that just met the Completeness Rule,
        `published=False` by default (FR-006)."""
        created_at = _now()
        story = Story(
            id=str(uuid.uuid4()),
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
            narrativeGuidance=narrative_guidance,
            startingPoint=starting_point,
            published=False,
            createdBy=draft.createdBy,
            createdAt=created_at,
            contentUpdatedAt=created_at,
        )
        self._container().upsert_item(story.to_dict())
        logger.info("Story persisted", extra={"story_id": story.id, "created_by": story.createdBy})
        return story

    def get_story(self, story_id: str) -> Optional[Story]:
        try:
            item = self._container().read_item(item=story_id, partition_key=story_id)
        except CosmosResourceNotFoundError:
            return None
        return Story.from_dict(item)

    def get_story_name(self, story_id: str) -> Optional[str]:
        """Just `name`, for callers that only need it for display (e.g. resolving a saved
        game's adventure name) — a projected query rather than `get_story`'s full point
        read of `worldPrompt`/`narrativeGuidance`/`chapters`/`rules`/etc."""
        rows = self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.name FROM c WHERE c.id = @id",
            params=[{"name": "@id", "value": story_id}],
            partition_key=story_id,
        )
        return rows[0].get("name") if rows else None

    def get_adventure_summary(self, story_id: str) -> Optional[dict[str, Any]]:
        """`id`, `name`, `published`, `characterTypes` only, for the player-facing
        adventure-detail endpoint — which never needs `worldPrompt`/`narrativeGuidance`/
        `rules`/`completionCriteria` — rather than `get_story`'s full point read.
        `published` defaults to `False` for a legacy row missing the field, matching
        `Story.from_dict`'s own default."""
        rows = self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.published, c.characterTypes FROM c WHERE c.id = @id",
            params=[{"name": "@id", "value": story_id}],
            partition_key=story_id,
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row.get("id"),
            "name": row.get("name"),
            "published": row.get("published", False),
            "characterTypes": row.get("characterTypes", []),
        }

    def list_summaries(self) -> list[dict[str, Any]]:
        """Summary shape only (`id`, `name`, `published`, `lastPublishedAt`, `createdAt`) —
        full detail is fetched via `get_story` (contracts/api.md)."""
        return self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.published, c.lastPublishedAt, c.createdAt FROM c WHERE c.entityType = 'Story'",
        )

    def can_publish(self, story: Story) -> bool:
        """FR-008 gate: a qualifying test play must exist since content was last saved."""
        return story.lastTestPlayedAt is not None and story.lastTestPlayedAt >= story.contentUpdatedAt

    def publish(self, story_id: str) -> Story | None | _PublishGateNotSatisfied:
        """Publish `story_id` (FR-003), idempotent (FR-006), gated by FR-008. Returns `None`
        if the story doesn't exist, `PUBLISH_GATE_NOT_SATISFIED` if the gate blocks it, or the
        updated `Story` on success."""
        story = self.get_story(story_id)
        if story is None:
            return None
        if not self.can_publish(story):
            return PUBLISH_GATE_NOT_SATISFIED
        story.published = True
        story.lastPublishedAt = _now()
        self._container().upsert_item(story.to_dict())
        return story

    def unpublish(self, story_id: str) -> Optional[Story]:
        """Unpublish `story_id` (FR-004), idempotent (FR-006); `lastPublishedAt` is left
        untouched (FR-012). No server-side precondition beyond the story existing."""
        story = self.get_story(story_id)
        if story is None:
            return None
        story.published = False
        self._container().upsert_item(story.to_dict())
        return story

    def delete_story(self, story_id: str) -> bool:
        """Permanently remove `story_id` (025-story-delete FR-003) — a hard delete, not a
        flag, unlike `unpublish` above (research.md Decision 1). Returns `False` for a
        story id that never existed or was already deleted, `True` on success."""
        try:
            self._container().delete_item(item=story_id, partition_key=story_id)
        except CosmosResourceNotFoundError:
            return False
        return True

    def _replaced_story(
        self, story: Story, configuration: StoryConfiguration, admin_oid: str, derived: DerivedContent
    ) -> Story:
        """The Content write operation (data-model.md → Content write): preserve the
        system-managed identity/publish fields, replace the authored set wholesale, and
        stamp the audit trail."""
        return Story(
            id=story.id,
            name=configuration.name,
            coverImageUrl=configuration.coverImageUrl,
            tone=configuration.tone,
            readingLevel=configuration.readingLevel,
            sessionLengthMinutes=configuration.sessionLengthMinutes,
            chapters=configuration.chapters,
            worldPrompt=configuration.worldPrompt,
            rules=configuration.rules,
            characterTypes=configuration.characterTypes,
            completionCriteria=configuration.completionCriteria,
            narrativeGuidance=derived.narrativeGuidance,
            startingPoint=derived.startingPoint,
            adminEditedFields=derived.adminEditedFields,
            published=story.published,
            lastPublishedAt=story.lastPublishedAt,
            createdBy=story.createdBy,
            createdAt=story.createdAt,
            contentUpdatedAt=_now(),
            lastTestPlayedAt=story.lastTestPlayedAt,
            lastUpdatedBy=admin_oid,
            contentVersion=story.contentVersion + 1,
        )

    def apply_content_write(
        self,
        story: Story,
        configuration: StoryConfiguration,
        admin_oid: str,
        derived: DerivedContent,
        *,
        exempt_from_staleness: bool = False,
    ) -> Story:
        """Apply a content write against `story.id` (wizard edit save, or an id-matched
        overwrite import), guarded by the Cosmos `_etag` (research.md §6). Each attempt
        re-reads the row fresh — closing the read-check-write window rather than trusting
        the caller's possibly-stale `story` — and checks its `contentVersion` against the
        version `story` was read at: a mismatch is genuine staleness (`StaleStoryError`,
        unless `exempt_from_staleness` — the import path, which never carries a version
        check). A matching version but a failed precondition means a concurrent
        publish/unpublish landed with a fresh `_etag`; the write is retried once against
        that fresh row, preserving its `published` state. A second precondition failure
        raises `WriteConflictError` (contracts/api.md → Write conflicts)."""
        expected_version = story.contentVersion
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            item = self._read_item(story.id)
            if item is None:
                raise StoryNotFoundError()
            current = Story.from_dict(item)
            if not exempt_from_staleness and current.contentVersion != expected_version:
                raise StaleStoryError()

            updated = self._replaced_story(current, configuration, admin_oid, derived)
            try:
                self._container().replace_item(
                    item=updated.id,
                    body=updated.to_dict(),
                    etag=item["_etag"],
                    match_condition=MatchConditions.IfNotModified,
                )
                return updated
            except CosmosAccessConditionFailedError:
                if attempt >= max_attempts:
                    raise WriteConflictError() from None

    def import_configuration(
        self,
        configuration: StoryConfiguration,
        admin_oid: str,
        confirm_overwrite_story_id: Optional[str],
        title: Optional[str],
    ) -> tuple[str, Story]:
        """Route an uploaded `StoryConfiguration` per research.md §7's table. Returns
        `("updated" | "created", story)`. Raises `StoryNotFoundError` for an id that
        matches nothing (`011` FR-004 as revised — never re-minted under a fresh id),
        `ConfirmationRequiredError`/`TitleRequiredError` for the missing-confirmation/
        missing-title cases (research.md §7's routing table)."""
        if configuration.id:
            if confirm_overwrite_story_id != configuration.id:
                raise ConfirmationRequiredError()
            story = self.get_story(configuration.id)
            if story is None:
                raise StoryNotFoundError()
            derived = self.derived_content(configuration, configuration.name, existing=story)
            updated = self.apply_content_write(
                story, configuration, admin_oid, derived, exempt_from_staleness=True
            )
            return "updated", updated

        if not title:
            raise TitleRequiredError()

        derived = self.derived_content(configuration, title)
        created_at = _now()
        story = Story(
            id=str(uuid.uuid4()),
            name=title,
            coverImageUrl=configuration.coverImageUrl,
            tone=configuration.tone,
            readingLevel=configuration.readingLevel,
            sessionLengthMinutes=configuration.sessionLengthMinutes,
            chapters=configuration.chapters,
            worldPrompt=configuration.worldPrompt,
            rules=configuration.rules,
            characterTypes=configuration.characterTypes,
            completionCriteria=configuration.completionCriteria,
            narrativeGuidance=derived.narrativeGuidance,
            startingPoint=derived.startingPoint,
            adminEditedFields=derived.adminEditedFields,
            published=False,
            createdBy=admin_oid,
            createdAt=created_at,
            contentUpdatedAt=created_at,
            lastUpdatedBy=None,
            contentVersion=1,
        )
        self._container().upsert_item(story.to_dict())
        return "created", story

    def list_published_summaries(self) -> list[dict[str, Any]]:
        """Player-facing `AdventureSummary` shape (006-adventure-and-character-setup
        data-model.md) — published stories only; never exposes admin-only fields like
        `published`/`createdAt` (FR-001, FR-006)."""
        return self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.tone, c.sessionLengthMinutes, c.readingLevel "
            "FROM c WHERE c.entityType = 'Story' AND c.published = true",
        )
