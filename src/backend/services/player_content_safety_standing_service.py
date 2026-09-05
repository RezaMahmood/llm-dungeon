"""PlayerContentSafetyStandingService — tracks each player's cross-session
content-safety-flagged submission count and any resulting 1-hour lockout
(008-core-gameplay research.md Decision 9, FR-013)."""

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
from backend.models.player_content_safety_standing import PlayerContentSafetyStanding
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("player_content_safety_standing_service")

FLAGS_BEFORE_LOCKOUT = 3
LOCKOUT_DURATION = datetime.timedelta(hours=1)
# Bounded, matching CosmosService._MAX_RETRIES — a conditional write that keeps losing
# must fail predictably rather than recursing until the stack gives out.
MAX_WRITE_ATTEMPTS = 3


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _format(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def describe_lockout(lockout_until: Optional[str]) -> str:
    """How long is left, in words. FR-013 requires the player be told clearly why they are
    locked out and for how long — and this audience is young players, so a raw UTC
    timestamp doesn't qualify. The machine-readable value is still returned alongside the
    message for any client that wants a countdown (contracts/api.md)."""
    if not lockout_until:
        return "You can try again a little later."
    remaining_seconds = (_parse(lockout_until) - _now()).total_seconds()
    if remaining_seconds <= 0:
        return "You can try again now."
    minutes = int(remaining_seconds // 60) + 1
    if minutes >= 55:
        return "You can play again in about an hour."
    if minutes == 1:
        return "You can play again in about a minute."
    return f"You can play again in about {minutes} minutes."


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
        for attempt in range(1, MAX_WRITE_ATTEMPTS + 1):
            try:
                item = container.read_item(item=player_id, partition_key=player_id)
            except CosmosResourceNotFoundError:
                standing = PlayerContentSafetyStanding(id=player_id, flaggedCount=1, lockoutUntil=None)
                if standing.flaggedCount >= FLAGS_BEFORE_LOCKOUT:
                    standing.lockoutUntil = _format(_now() + LOCKOUT_DURATION)
                try:
                    container.create_item(standing.to_dict())
                    return standing
                except CosmosResourceExistsError:
                    # Another request created the document first; re-read and increment.
                    logger.warning("Concurrent create of the standing for player %s; retrying", player_id)
                    continue

            etag = item["_etag"]
            standing = PlayerContentSafetyStanding.from_dict(item)
            standing.flaggedCount += 1
            prior_lockout_expired = standing.lockoutUntil is not None and _parse(standing.lockoutUntil) <= _now()
            if standing.flaggedCount >= FLAGS_BEFORE_LOCKOUT and (
                standing.lockoutUntil is None or prior_lockout_expired
            ):
                standing.lockoutUntil = _format(_now() + LOCKOUT_DURATION)
            try:
                container.replace_item(
                    item=player_id,
                    body=standing.to_dict(),
                    etag=etag,
                    match_condition=MatchConditions.IfNotModified,
                )
                return standing
            except CosmosAccessConditionFailedError:
                logger.warning(
                    "Concurrent flag write for player %s (attempt %d/%d)", player_id, attempt, MAX_WRITE_ATTEMPTS
                )

        # Deliberate: the player's turn already produced a safe deflection, so losing this
        # strike is a better outcome than failing their request outright. Logged at error
        # because sustained contention here means the lockout is under-counting.
        logger.error("Gave up recording a content-safety flag for player %s after %d attempts", player_id, MAX_WRITE_ATTEMPTS)
        return self.get_standing(player_id) or PlayerContentSafetyStanding(id=player_id)
