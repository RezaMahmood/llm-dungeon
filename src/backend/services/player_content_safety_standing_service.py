"""PlayerContentSafetyStandingService — tracks each player's cross-session
content-safety-flagged submission count and any resulting 1-hour lockout
(008-core-gameplay research.md Decision 9, FR-013)."""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.models.player_content_safety_standing import PlayerContentSafetyStanding
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("player_content_safety_standing_service")

FLAGS_BEFORE_LOCKOUT = 3
LOCKOUT_DURATION = datetime.timedelta(hours=1)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _format(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


class PlayerContentSafetyStandingService:
    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or CosmosService()

    def _container(self):
        return self._cosmos.get_container(config.PLAYER_CONTENT_SAFETY_STANDINGS_CONTAINER)

    def get_standing(self, player_id: str) -> Optional[PlayerContentSafetyStanding]:
        try:
            item = self._container().read_item(item=player_id, partition_key=player_id)
        except CosmosResourceNotFoundError:
            return None
        return PlayerContentSafetyStanding.from_dict(item)

    def is_locked_out(self, player_id: str) -> bool:
        standing = self.get_standing(player_id)
        if standing is None or standing.lockoutUntil is None:
            return False
        return _parse(standing.lockoutUntil) > _now()

    def record_flag(self, player_id: str) -> PlayerContentSafetyStanding:
        """Increments `flaggedCount` for `player_id`, creating the document lazily on the
        first flag. Sets `lockoutUntil = now + 1h` on the 3rd flag, and again on any later
        flagged submission that only occurs once a prior lockout has expired (both call
        sites reject with 423 before any LLM call — and therefore before any flag — while
        `lockoutUntil` is still in the future)."""
        container = self._container()
        try:
            item = container.read_item(item=player_id, partition_key=player_id)
        except CosmosResourceNotFoundError:
            standing = PlayerContentSafetyStanding(id=player_id, flaggedCount=1, lockoutUntil=None)
            if standing.flaggedCount >= FLAGS_BEFORE_LOCKOUT:
                standing.lockoutUntil = _format(_now() + LOCKOUT_DURATION)
            container.create_item(standing.to_dict())
            return standing

        etag = item["_etag"]
        standing = PlayerContentSafetyStanding.from_dict(item)
        standing.flaggedCount += 1
        was_locked_out_before = standing.lockoutUntil is not None and _parse(standing.lockoutUntil) <= _now()
        if standing.flaggedCount >= FLAGS_BEFORE_LOCKOUT and (standing.lockoutUntil is None or was_locked_out_before):
            standing.lockoutUntil = _format(_now() + LOCKOUT_DURATION)
        try:
            container.replace_item(
                item=player_id,
                body=standing.to_dict(),
                etag=etag,
                match_condition=MatchConditions.IfNotModified,
            )
        except CosmosAccessConditionFailedError:
            logger.warning("Concurrent flag write for player %s; retrying", player_id)
            return self.record_flag(player_id)
        return standing
