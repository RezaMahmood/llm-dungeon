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
            createdBy=draft.createdBy,
            createdAt=_now(),
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

    def list_summaries(self) -> list[dict[str, Any]]:
        """Summary shape only (`id`, `name`, `published`, `createdAt`) — full detail is
        fetched via `get_story` (contracts/api.md)."""
        return self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.published, c.createdAt FROM c WHERE c.entityType = 'Story'",
        )

    def list_published_summaries(self) -> list[dict[str, Any]]:
        """Player-facing `AdventureSummary` shape (006-adventure-and-character-setup
        data-model.md) — published stories only; never exposes admin-only fields like
        `published`/`createdAt` (FR-001, FR-006)."""
        return self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.tone, c.sessionLengthMinutes, c.readingLevel "
            "FROM c WHERE c.entityType = 'Story' AND c.published = true",
        )
