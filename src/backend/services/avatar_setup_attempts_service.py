"""AvatarSetupAttemptsService — bounds the number of model-backed avatar-description
validation attempts within a single setup, per (player, story) pair
(032-story-archetypes-player-avatar research.md Decision 3)."""

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
from backend.models.avatar_setup_attempts import AvatarSetupAttempts
from backend.services.cosmos_service import CosmosService, shared_cosmos_service

logger = logging.getLogger("avatar_setup_attempts_service")

# Bounded, matching this codebase's other conditional-write retry loops
# (PlayerContentSafetyStandingService, StoryService) — a write that keeps losing its
# `_etag` race must fail predictably rather than recursing until the stack gives out.
MAX_WRITE_ATTEMPTS = 3

# The cap counts attempts within a rolling window rather than for all time. The counter
# is otherwise only cleared by a successful session creation — which a capped player can
# never reach, since the cap is checked before the validation that would let them through
# — so a permanent counter turned the guard rail into a permanent ban on that adventure,
# while the player was told a short break would help (issue #361 convergence, FR-014 and
# its Edge Case "not left without a next action"). Long enough that sustained probing
# stays capped; short enough that the break the message promises actually works.
ATTEMPT_WINDOW = datetime.timedelta(minutes=30)


def _doc_id(player_id: str, story_id: str) -> str:
    return f"{player_id}:{story_id}"


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _format(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def _window_expired(record: AvatarSetupAttempts) -> bool:
    """True when `record`'s counting window has closed, so its count no longer applies.
    A document written before `windowStartedAt` existed has no window and is treated as
    expired — which releases anyone the permanent counter had already stranded."""
    if record.windowStartedAt is None:
        return True
    try:
        return _now() - _parse(record.windowStartedAt) >= ATTEMPT_WINDOW
    except (ValueError, TypeError):
        # An unreadable timestamp is treated the same as a missing one: expired, so a
        # malformed document can never be what keeps a player locked out. TypeError as
        # well as ValueError — a non-string value (an epoch number, say) raises the
        # former, and letting it escape would 500 every start request for this pair,
        # which is a worse lockout than the one this window exists to prevent.
        logger.warning("Unparseable windowStartedAt on %s; treating the window as expired", record.id)
        return True


class AvatarSetupAttemptsService:
    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or shared_cosmos_service()

    def _container(self):
        return self._cosmos.get_container(config.AVATAR_SETUP_ATTEMPTS_CONTAINER)

    def get_attempts(self, player_id: str, story_id: str) -> int:
        """Attempts counted inside the current window. A closed window reads as zero, so
        the cap releases on its own rather than waiting for a session that a capped player
        cannot create."""
        doc_id = _doc_id(player_id, story_id)
        try:
            item = self._container().read_item(item=doc_id, partition_key=doc_id)
        except CosmosResourceNotFoundError:
            return 0
        record = AvatarSetupAttempts.from_dict(item)
        if _window_expired(record):
            return 0
        return record.modelBackedAttempts

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
                    id=doc_id,
                    playerId=player_id,
                    storyId=story_id,
                    modelBackedAttempts=1,
                    windowStartedAt=_format(_now()),
                )
                try:
                    container.create_item(record.to_dict())
                    return record.modelBackedAttempts
                except CosmosResourceExistsError:
                    logger.warning("Concurrent create of avatar-setup-attempts for %s; retrying", doc_id)
                    continue

            etag = item["_etag"]
            record = AvatarSetupAttempts.from_dict(item)
            if _window_expired(record):
                # First attempt of a new window: restart the count rather than adding to
                # one that has already lapsed.
                record.modelBackedAttempts = 1
                record.windowStartedAt = _format(_now())
            else:
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
