"""StoryService — persist a generated Story, fetch one by id, list summaries."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Optional

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.config import config
from backend.models.story import Story
from backend.models.story_draft import StoryDraft
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("story_service")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StoryService:
    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or CosmosService()

    def _container(self):
        return self._cosmos.get_container(config.STORIES_CONTAINER)

    def create_story(self, draft: StoryDraft, narrative_guidance: str) -> Story:
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
            published=False,
            contentUpdatedAt=created_at,
            createdBy=draft.createdBy,
            createdAt=created_at,
        )
        self._container().upsert_item(story.to_dict())
        logger.info("Story persisted", extra={"story_id": story.id, "created_by": story.createdBy})
        return story

    @staticmethod
    def can_publish(story: Story) -> bool:
        """FR-008 gate: a qualifying test play recorded since the content was last saved
        (005-story-publishing data-model.md). `017-story-publish-test-play-gate` owns
        writing `lastTestPlayedAt`; until it ships this is always False (spec-correct)."""
        return story.lastTestPlayedAt is not None and story.lastTestPlayedAt >= story.contentUpdatedAt

    def publish(self, story_id: str) -> tuple[Optional[Story], bool]:
        """Returns (story, gate_satisfied). `story` is None if not found. On a gate
        failure the story is returned unchanged (409, FR-011) rather than written."""
        story = self.get_story(story_id)
        if story is None:
            return None, False
        if not self.can_publish(story):
            return story, False
        story.published = True
        story.lastPublishedAt = _now()
        self._container().upsert_item(story.to_dict())
        logger.info("Story published", extra={"story_id": story.id})
        return story, True

    def unpublish(self, story_id: str) -> Optional[Story]:
        """Idempotent (FR-006); leaves `lastPublishedAt` untouched (FR-012); never affects
        in-progress play sessions (FR-005, enforced simply by not touching them here)."""
        story = self.get_story(story_id)
        if story is None:
            return None
        story.published = False
        self._container().upsert_item(story.to_dict())
        logger.info("Story unpublished", extra={"story_id": story.id})
        return story

    def get_story(self, story_id: str) -> Optional[Story]:
        try:
            item = self._container().read_item(item=story_id, partition_key=story_id)
        except CosmosResourceNotFoundError:
            return None
        return Story.from_dict(item)

    def list_summaries(self) -> list[dict[str, Any]]:
        """Summary shape only (`id`, `name`, `published`, `createdAt`) — full detail is
        fetched via `get_story` (contracts/api.md)."""
        return self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.published, c.createdAt FROM c WHERE c.entityType = 'Story'",
        )
