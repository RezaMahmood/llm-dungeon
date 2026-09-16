"""StoredAvatarDescriptionService — remembers a player's most recently used avatar
description per adventure, offered back as a setup prefill
(034-avatar-memory-and-visibility research.md Decision 1).

Keyed exactly like `AvatarSetupAttemptsService` (`032`): one document per `(playerId,
storyId)` pair, id `f"{playerId}:{storyId}"`, upserted via a bounded `_etag` read-modify-
write."""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from azure.core import MatchConditions
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from backend.config import config
from backend.models.stored_avatar_description import StoredAvatarDescription
from backend.services.cosmos_service import CosmosService, shared_cosmos_service

logger = logging.getLogger("stored_avatar_description_service")

# Bounded, matching this codebase's other conditional-write retry loops
# (AvatarSetupAttemptsService, PlayerContentSafetyStandingService, StoryService).
MAX_WRITE_ATTEMPTS = 3


def _doc_id(player_id: str, story_id: str) -> str:
    return f"{player_id}:{story_id}"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StoredAvatarDescriptionService:
    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or shared_cosmos_service()

    def _container(self):
        return self._cosmos.get_container(config.STORED_AVATAR_DESCRIPTIONS_CONTAINER)

    def get(self, player_id: str, story_id: str) -> Optional[str]:
        doc_id = _doc_id(player_id, story_id)
        try:
            item = self._container().read_item(item=doc_id, partition_key=doc_id)
        except CosmosResourceNotFoundError:
            return None
        return StoredAvatarDescription.from_dict(item).description

    def store(self, player_id: str, story_id: str, description: str) -> None:
        """Upserts the player's stored description for `story_id`, replacing whatever was
        there before (FR-005) — never called until a session has actually been created
        with `description` (FR-012)."""
        doc_id = _doc_id(player_id, story_id)
        container = self._container()
        for attempt in range(1, MAX_WRITE_ATTEMPTS + 1):
            try:
                item = container.read_item(item=doc_id, partition_key=doc_id)
            except CosmosResourceNotFoundError:
                record = StoredAvatarDescription(
                    id=doc_id, playerId=player_id, storyId=story_id, description=description, updatedAt=_now()
                )
                try:
                    container.create_item(record.to_dict())
                    return
                except CosmosResourceExistsError:
                    logger.warning("Concurrent create of stored-avatar-description for %s; retrying", doc_id)
                    continue

            etag = item["_etag"]
            record = StoredAvatarDescription.from_dict(item)
            record.description = description
            record.updatedAt = _now()
            try:
                container.replace_item(
                    item=doc_id,
                    body=record.to_dict(),
                    etag=etag,
                    match_condition=MatchConditions.IfNotModified,
                )
                return
            except CosmosAccessConditionFailedError:
                logger.warning(
                    "Concurrent stored-avatar-description write for %s (attempt %d/%d)",
                    doc_id,
                    attempt,
                    MAX_WRITE_ATTEMPTS,
                )

        # Deliberate: losing this write on sustained contention only costs the player one
        # missed prefill next time, not correctness of anything already stored — not worth
        # failing the session-creation call that triggered it.
        logger.error("Gave up storing an avatar description for %s after %d attempts", doc_id, MAX_WRITE_ATTEMPTS)

    def delete_for_story(self, story_id: str) -> int:
        """Cascade for a story delete (FR-009): permanently remove every stored
        description for `story_id`, regardless of which player owns it. Returns the count
        actually removed. Idempotent per row, mirroring
        `PlaySessionService.delete_active_sessions_for_adventure`."""
        rows = self._cosmos.query(
            config.STORED_AVATAR_DESCRIPTIONS_CONTAINER,
            "SELECT c.id FROM c WHERE c.storyId = @storyId",
            params=[{"name": "@storyId", "value": story_id}],
        )
        container = self._container()
        removed = 0
        for row in rows:
            try:
                container.delete_item(item=row["id"], partition_key=row["id"])
                removed += 1
            except CosmosResourceNotFoundError:
                continue
        return removed
