"""AvatarSetupAttemptsService — bounds the number of model-backed avatar-description
validation attempts within a single setup, per (player, story) pair
(032-story-archetypes-player-avatar research.md Decision 3)."""

from __future__ import annotations

import logging
from typing import Optional

from azure.core import MatchConditions
from azure.cosmos.exceptions import (
    CosmosAccessConditionFailedError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)

from backend.config import config
from backend.models.avatar_setup_attempts import AvatarSetupAttempts
from backend.services.cosmos_service import CosmosService, shared_cosmos_service

logger = logging.getLogger("avatar_setup_attempts_service")

# Bounded, matching this codebase's other conditional-write retry loops
# (PlayerContentSafetyStandingService, StoryService) — a write that keeps losing its
# `_etag` race must fail predictably rather than recursing until the stack gives out.
MAX_WRITE_ATTEMPTS = 3


def _doc_id(player_id: str, story_id: str) -> str:
    return f"{player_id}:{story_id}"


class AvatarSetupAttemptsService:
    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or shared_cosmos_service()

    def _container(self):
        return self._cosmos.get_container(config.AVATAR_SETUP_ATTEMPTS_CONTAINER)

    def get_attempts(self, player_id: str, story_id: str) -> int:
        doc_id = _doc_id(player_id, story_id)
        try:
            item = self._container().read_item(item=doc_id, partition_key=doc_id)
        except CosmosResourceNotFoundError:
            return 0
        return AvatarSetupAttempts.from_dict(item).modelBackedAttempts

    def record_attempt(self, player_id: str, story_id: str) -> int:
        """Increments and returns the model-backed attempt count for `(player_id,
        story_id)`, creating the document lazily on the first attempt. Never called for a
        cost-free rejection (FR-010, FR-014)."""
        doc_id = _doc_id(player_id, story_id)
        container = self._container()
        for attempt in range(1, MAX_WRITE_ATTEMPTS + 1):
            try:
                item = container.read_item(item=doc_id, partition_key=doc_id)
            except CosmosResourceNotFoundError:
                record = AvatarSetupAttempts(
                    id=doc_id, playerId=player_id, storyId=story_id, modelBackedAttempts=1
                )
                try:
                    container.create_item(record.to_dict())
                    return record.modelBackedAttempts
                except CosmosResourceExistsError:
                    logger.warning("Concurrent create of avatar-setup-attempts for %s; retrying", doc_id)
                    continue

            etag = item["_etag"]
            record = AvatarSetupAttempts.from_dict(item)
            record.modelBackedAttempts += 1
            try:
                container.replace_item(
                    item=doc_id,
                    body=record.to_dict(),
                    etag=etag,
                    match_condition=MatchConditions.IfNotModified,
                )
                return record.modelBackedAttempts
            except CosmosAccessConditionFailedError:
                logger.warning(
                    "Concurrent avatar-setup-attempts write for %s (attempt %d/%d)",
                    doc_id,
                    attempt,
                    MAX_WRITE_ATTEMPTS,
                )

        # Deliberate: undercounting the cap on sustained write contention is preferable to
        # failing the player's setup attempt outright — the cap is a guard rail, not a
        # security boundary (spec.md Assumptions).
        logger.error("Gave up recording an avatar-setup attempt for %s after %d attempts", doc_id, MAX_WRITE_ATTEMPTS)
        return self.get_attempts(player_id, story_id)

    def clear(self, player_id: str, story_id: str) -> None:
        """Called once a session is successfully created, so a later, separate setup
        against the same adventure starts fresh."""
        doc_id = _doc_id(player_id, story_id)
        try:
            self._container().delete_item(item=doc_id, partition_key=doc_id)
        except CosmosResourceNotFoundError:
            pass
