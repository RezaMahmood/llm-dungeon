"""StoryService — explicit Save (create/update), Abandon (delete), cover-image upload,
fetch, and list, per the Session 2026-08-30 redesign (FR-004, FR-009, FR-012, FR-013/014).

Replaces the earlier auto-generate-on-completeness design: there is no more StoryDraft
container or LLM-driven persistence step here — a Story is written to Cosmos only when an
administrator explicitly Saves, and any subset of fields may be present at that point."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Optional

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.config import config
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.blob_service import BlobService
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("story_service")

# Story fields settable directly via create/update (data-model.md) — characterTypes/
# completionCriteria are handled separately since they need Shared-Structure validation,
# not a plain setattr.
PATCHABLE_FIELDS = {
    "name",
    "coverImageUrl",
    "tone",
    "readingLevel",
    "sessionLengthMinutes",
    "chapters",
    "outline",
    "rules",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StoryValidationError(ValueError):
    """A field failed Shared Structure validation — the caller maps this to a 422
    `invalid_field` response; no partial merge happens."""


class StoryService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        blob_service: Optional[BlobService] = None,
    ) -> None:
        self._cosmos = cosmos_service or CosmosService()
        self._blob = blob_service or BlobService()

    def _container(self):
        return self._cosmos.get_container(config.STORIES_CONTAINER)

    def _apply_fields(self, story: Story, updates: dict[str, Any]) -> None:
        for field_name in PATCHABLE_FIELDS:
            if field_name in updates:
                setattr(story, field_name, updates[field_name])

        if "characterTypes" in updates:
            raw = updates["characterTypes"] or []
            try:
                story.characterTypes = [CharacterType.from_dict(ct) for ct in raw]
            except (ValueError, KeyError, TypeError) as exc:
                raise StoryValidationError(f"characterTypes: {exc}") from exc

        if "completionCriteria" in updates:
            raw = updates["completionCriteria"]
            if raw is None:
                story.completionCriteria = None
            else:
                try:
                    story.completionCriteria = CompletionCriteria.from_dict(raw)
                except (ValueError, KeyError, TypeError) as exc:
                    raise StoryValidationError(f"completionCriteria: {exc}") from exc

    def create_story(self, name: str, created_by_email: str, updates: Optional[dict[str, Any]] = None) -> Story:
        """First Save for a new story (FR-004). `name` is the only required field
        (FR-009); every other field is optional and may be filled in over later Saves."""
        if not name:
            raise StoryValidationError("name is required")

        now = _now()
        story = Story(
            id=str(uuid.uuid4()),
            name=name,
            createdBy=created_by_email,
            createdAt=now,
            updatedBy=created_by_email,
            updatedAt=now,
        )
        if updates:
            self._apply_fields(story, {k: v for k, v in updates.items() if k != "name"})

        self._container().upsert_item(story.to_dict())
        logger.info("Story created", extra={"story_id": story.id})
        return story

    def update_story(self, story_id: str, updated_by_email: str, updates: dict[str, Any]) -> Optional[Story]:
        """A later Save for an existing story (FR-004) — updates only the fields
        supplied, stamping `updatedBy`/`updatedAt`. Returns `None` if the story no longer
        exists (e.g. Abandoned from another tab/session)."""
        story = self.get_story(story_id)
        if story is None:
            return None

        if "name" in updates and not updates["name"]:
            raise StoryValidationError("name cannot be cleared")

        self._apply_fields(story, updates)
        story.updatedBy = updated_by_email
        story.updatedAt = _now()

        self._container().upsert_item(story.to_dict())
        logger.info("Story updated", extra={"story_id": story.id})
        return story

    def delete_story(self, story_id: str) -> None:
        """Abandon (FR-013/014). Idempotent: deleting a story that was never saved (or
        already deleted) is a no-op, matching the Edge Case that Abandon always succeeds
        even when there is nothing to delete."""
        try:
            self._container().delete_item(item=story_id, partition_key=story_id)
            logger.info("Story deleted (abandoned)", extra={"story_id": story_id})
        except CosmosResourceNotFoundError:
            pass

    def upload_cover_image(
        self,
        story_id: str,
        updated_by_email: str,
        filename: str,
        content: bytes,
        content_type: Optional[str],
    ) -> Optional[Story]:
        """Writes an uploaded cover image to blob storage and stores the reference on the
        story record (FR-009). Returns `None` if the story doesn't exist yet — the story
        must be Saved (so an id exists) before a cover image can be attached to it."""
        story = self.get_story(story_id)
        if story is None:
            return None

        url = self._blob.upload_cover_image(story_id, filename, content, content_type)
        story.coverImageUrl = url
        story.updatedBy = updated_by_email
        story.updatedAt = _now()
        self._container().upsert_item(story.to_dict())
        return story

    def get_story(self, story_id: str) -> Optional[Story]:
        try:
            item = self._container().read_item(item=story_id, partition_key=story_id)
        except CosmosResourceNotFoundError:
            return None
        return Story.from_dict(item)

    def list_summaries(self) -> list[dict[str, Any]]:
        """Summary shape only (`id`, `name`, `published`, `createdAt`) — full detail is
        fetched via `get_story`."""
        return self._cosmos.query(
            config.STORIES_CONTAINER,
            "SELECT c.id, c.name, c.published, c.createdAt FROM c WHERE c.entityType = 'Story'",
        )
