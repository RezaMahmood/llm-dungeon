"""PlaySessionService — session lifecycle (creation, interaction submission, resume),
cross-player and per-player (FR-015) exclusivity, rate limiting, content-safety lockout
enforcement, completion-rule evaluation, and 20-turn summarization
(008-core-gameplay-done research.md, data-model.md)."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Optional

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.models.play_session import CheckpointMarker, PlayerInteraction, PlaySession
from backend.models.player_content_safety_standing import PlayerContentSafetyStanding
from backend.services.cosmos_service import CosmosService
from backend.services.llm_service import LLMContentFilteredError, LLMOutputError, LLMRateLimitError, LLMService
from backend.services.player_content_safety_standing_service import (
    PlayerContentSafetyStandingService,
    describe_lockout,
)
from backend.services.story_service import StoryService

logger = logging.getLogger("play_session_service")

MAX_CHARACTER_NAME_LENGTH = 50
# Well above real typing/round-trip time, well below anything a legitimate player would
# hit (research.md Decision 4) — a best-effort, request-shape limiter, not a distributed
# rate-limiter.
MIN_INTERACTION_INTERVAL_SECONDS = 2
# Starting an adventure is a rare, deliberate act, and each one costs an opening-narrative
# LLM call — so it gets a longer floor than a turn does. Without this, session creation is
# the cheapest way for one player to drive unbounded model spend (FR-005).
MIN_SESSION_CREATION_INTERVAL_SECONDS = 10
SUMMARIZE_EVERY_N_TURNS = 20

# A content-filtered submission is never stored verbatim. `turns[].playerInput` is replayed
# into the prompt for every later turn, so keeping the flagged text would re-trip the filter
# on each one and walk the player into a lockout they didn't earn (FR-004, FR-013).
REDACTED_PLAYER_INPUT = "[removed by content safety]"

FIELD_MESSAGES = {
    "adventureId": "Select an adventure.",
    "characterName_required": "Character name is required.",
    "characterName_too_long": f"Character name must be {MAX_CHARACTER_NAME_LENGTH} characters or fewer.",
    "characterType_required": "Select a character type for this adventure.",
    "characterType_invalid": "Choose one of this adventure's character types.",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_dt() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


# --- Errors — the API layer (api/game/sessions.py) maps each to its contracts/api.md shape ---


class ContentSafetyLockoutError(Exception):
    def __init__(self, standing: PlayerContentSafetyStanding) -> None:
        super().__init__("Player is within an active content-safety lockout")
        self.lockout_until = standing.lockoutUntil


class InvalidSetupError(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Setup is incomplete or invalid")
        self.fields = fields


class AdventureNotFoundError(Exception):
    pass


class StoryUnpublishedError(Exception):
    """025-story-delete FR-005/FR-008: the session's story still exists but is currently
    unpublished. Unlike a delete, the session itself is never touched — this is checked
    fresh on every relevant request (research.md Decision 3, 4)."""

    pass


class NarrativeUnavailableError(Exception):
    pass


class InvalidInputError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class SessionConcludedError(Exception):
    pass


class SessionInactiveError(Exception):
    pass


class InteractionInProgressError(Exception):
    pass


class RateLimitedError(Exception):
    pass


class AlreadyActiveError(Exception):
    pass


class CheckpointUnavailableError(Exception):
    pass


# A checkpoint's label falls back to this when the session's latest turn carries no
# location (research.md Decision 2) — mirrors how `_deflection_turn_data` already falls
# back to "Unknown" for the same missing-location case.
DEFAULT_CHECKPOINT_LABEL = "Your story"


class PlaySessionService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        story_service: Optional[StoryService] = None,
        llm_service: Optional[LLMService] = None,
        player_content_safety_standing_service: Optional[PlayerContentSafetyStandingService] = None,
    ) -> None:
        self._cosmos = cosmos_service or CosmosService()
        self._stories = story_service or StoryService(cosmos_service=self._cosmos)
        self._llm = llm_service or LLMService()
        self._safety = player_content_safety_standing_service or PlayerContentSafetyStandingService(
            cosmos_service=self._cosmos
        )

    def _container(self):
        return self._cosmos.get_container(config.PLAY_SESSIONS_CONTAINER)

    def _read_item(self, session_id: str) -> Optional[dict[str, Any]]:
        try:
            return self._container().read_item(item=session_id, partition_key=session_id)
        except CosmosResourceNotFoundError:
            return None

    # --- Session creation (T042) ---

    def create_session(
        self, adventure_id: str, character_name: str, character_type: str, player_id: str
    ) -> PlaySession:
        if self._safety.is_locked_out(player_id):
            raise ContentSafetyLockoutError(self._safety.get_standing(player_id))

        # A missing adventure id is a malformed request, not a missing adventure — the
        # retired game/start reported it as a field error and the contract still does.
        if not adventure_id:
            raise InvalidSetupError({"adventureId": FIELD_MESSAGES["adventureId"]})

        story = self._stories.get_story(adventure_id)
        if story is None or not story.published:
            raise AdventureNotFoundError()

        trimmed_name = (character_name or "").strip()
        fields: dict[str, str] = {}
        if not trimmed_name:
            fields["characterName"] = FIELD_MESSAGES["characterName_required"]
        elif len(trimmed_name) > MAX_CHARACTER_NAME_LENGTH:
            fields["characterName"] = FIELD_MESSAGES["characterName_too_long"]

        valid_type_names = {ct.name for ct in story.characterTypes}
        if not character_type:
            fields["characterType"] = FIELD_MESSAGES["characterType_required"]
        elif character_type not in valid_type_names:
            fields["characterType"] = FIELD_MESSAGES["characterType_invalid"]

        if fields:
            raise InvalidSetupError(fields)

        # Checked after validation (so a mistyped name still gets its field error) but
        # before the opening-narrative call, which is the cost this protects.
        most_recent_start = self._most_recent_session_start(player_id)
        if (
            most_recent_start
            and (_now_dt() - _parse(most_recent_start)).total_seconds() < MIN_SESSION_CREATION_INTERVAL_SECONDS
        ):
            raise RateLimitedError()

        now = _now()
        session = PlaySession(
            id=str(uuid.uuid4()),
            adventureId=story.id,
            playerId=player_id,
            characterName=trimmed_name,
            characterType=character_type,
            startedAt=now,
            lastInteractionAt=now,
            isActiveForPlayer=True,
        )

        try:
            turn_data = self._llm.generate_gameplay_turn(story, session, None)
        except LLMContentFilteredError as exc:
            # No player input exists yet, so this is the adventure's own content tripping
            # the filter. That is not the player's doing, so it must not count toward
            # their safety standing (FR-013) — it is simply an unavailable narrative.
            logger.warning("Opening narrative was content-filtered for adventure %s", story.id)
            raise NarrativeUnavailableError() from exc
        except (LLMOutputError, LLMRateLimitError) as exc:
            raise NarrativeUnavailableError() from exc

        session.turns.append(self._turn_from_llm_data(0, None, turn_data, now))
        self._container().create_item(session.to_dict())
        self._deactivate_other_active_sessions(player_id, exclude_session_id=session.id)
        logger.info("Play session created", extra={"session_id": session.id, "adventure_id": adventure_id})
        return session

    # --- Interaction submission (T043, T072-T074) ---

    def submit_interaction(self, session_id: str, player_id: str, raw_input: str) -> tuple[PlaySession, Optional[dict]]:
        if self._safety.is_locked_out(player_id):
            raise ContentSafetyLockoutError(self._safety.get_standing(player_id))

        trimmed_input = (raw_input or "").strip()
        if not trimmed_input:
            raise InvalidInputError()

        item = self._read_item(session_id)
        if item is None:
            raise SessionNotFoundError()
        etag = item["_etag"]
        session = PlaySession.from_dict(item)

        if session.playerId != player_id:
            raise ForbiddenError()
        if not session.isActiveForPlayer:
            raise SessionInactiveError()
        if session.status == "concluded":
            raise SessionConcludedError()
        if (_now_dt() - _parse(session.lastInteractionAt)).total_seconds() < MIN_INTERACTION_INTERVAL_SECONDS:
            raise RateLimitedError()
        if session.interactionInProgress:
            raise InteractionInProgressError()
        story = self._check_story_available(session)

        session.interactionInProgress = True
        try:
            claimed = self._container().replace_item(
                item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
            )
        except CosmosAccessConditionFailedError as exc:
            raise InteractionInProgressError() from exc

        try:
            return self._generate_and_persist_turn(story, session, player_id, trimmed_input, claimed["_etag"])
        except Exception:
            # Only the turn's own write clears `interactionInProgress`, so any failure
            # between the claim above and that write would leave the session rejecting
            # every later interaction with 409 for good.
            self._release_claim(session.id)
            raise

    def _check_story_available(self, session: PlaySession):
        """025-story-delete FR-005/FR-007/FR-008: raises `AdventureNotFoundError` if the
        session's story is gone (a delete's cascade normally removes the session itself
        first, so this is the narrow race where a request is already in flight) or
        `StoryUnpublishedError` if it still exists but is currently unpublished. A
        concluded session is exempt (data-model.md Validation Rules) — its outcome never
        changes based on its story's later published/deleted state. Never mutates
        `session`. Returns the story on success (or `None` for an exempt concluded
        session), for the caller to reuse."""
        if session.status == "concluded":
            return None
        story = self._stories.get_story(session.adventureId)
        if story is None:
            raise AdventureNotFoundError()
        if not story.published:
            raise StoryUnpublishedError()
        return story

    def _generate_and_persist_turn(
        self, story, session: PlaySession, player_id: str, trimmed_input: str, etag: str
    ) -> tuple[PlaySession, Optional[dict]]:
        now = _now()
        completion_reason: Optional[dict[str, Any]] = None

        if self._duration_ceiling_reached(story, session):
            try:
                turn_data = self._llm.generate_gameplay_turn(
                    story,
                    session,
                    trimmed_input,
                    concluding_reason="the session's configured time limit has been reached",
                )
            except (LLMOutputError, LLMRateLimitError) as exc:
                raise NarrativeUnavailableError() from exc
            turn = self._turn_from_llm_data(len(session.turns), trimmed_input, turn_data, now)
            completion_reason = {"type": "duration", "detail": None}
        else:
            try:
                turn_data = self._llm.generate_gameplay_turn(story, session, trimmed_input)
                turn = self._turn_from_llm_data(len(session.turns), trimmed_input, turn_data, now)
                completion_reason = self._evaluate_completion(story, session, turn_data)
            except LLMContentFilteredError:
                standing = self._safety.record_flag(player_id)
                turn_data = self._deflection_turn_data(session, standing)
                turn = self._turn_from_llm_data(len(session.turns), REDACTED_PLAYER_INPUT, turn_data, now)
            except (LLMOutputError, LLMRateLimitError) as exc:
                raise NarrativeUnavailableError() from exc

        session.turns.append(turn)
        session.lastInteractionAt = now
        if completion_reason is not None:
            session.status = "concluded"
            session.completionReason = completion_reason
            session.endedAt = now

        self._summarize_if_due(story, session)

        session.interactionInProgress = False
        self._container().replace_item(
            item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
        )
        return session, completion_reason

    def _summarize_if_due(self, story, session: PlaySession) -> None:
        """Fold the turns since the last summary into a fresh one every
        SUMMARIZE_EVERY_N_TURNS turns (FR-014). The opening narrative counts as a turn, so
        the first summary covers turn 0 plus the next 19."""
        last_turn_number = session.turns[-1].turnNumber
        if len(session.turns) % SUMMARIZE_EVERY_N_TURNS != 0 or last_turn_number <= session.summarizedThroughTurn:
            return
        try:
            summary = self._llm.summarize_session_history(story, session)
        except (LLMOutputError, LLMRateLimitError):
            # Summarizing only bounds future context; it is not part of the turn the
            # player just earned, so a failure must not cost them that turn. The next
            # summarization picks up everything still unsummarized.
            logger.warning("Summarization failed for session %s; keeping the full history", session.id)
            return
        session.summary = summary
        # data-model.md defines this as the turnNumber of the last turn folded in. Using
        # the turn count instead would be one too high, and the `turnNumber <=` filters in
        # llm_service would then also swallow the turn generated right after this one.
        session.summarizedThroughTurn = last_turn_number

    def _release_claim(self, session_id: str) -> None:
        """Best-effort release of a claimed interaction after a failed turn, so one
        transient failure doesn't make the session permanently unplayable."""
        try:
            item = self._read_item(session_id)
            if item is None:
                return
            # Round-tripped through the model rather than mutating the raw read: Cosmos's
            # own `_etag`/`_rid`/`_self`/`_ts` travel on the read result and are not ours
            # to write back as document fields.
            session = PlaySession.from_dict(item)
            session.interactionInProgress = False
            self._container().replace_item(
                item=session_id,
                body=session.to_dict(),
                etag=item["_etag"],
                match_condition=MatchConditions.IfNotModified,
            )
        except Exception:  # noqa: BLE001 - must never mask the failure that brought us here
            logger.exception("Could not release the interaction claim on session %s", session_id)

    # --- Resume (T057, FR-015) ---

    def resume_session(self, session_id: str, player_id: str) -> PlaySession:
        item = self._read_item(session_id)
        if item is None:
            raise SessionNotFoundError()
        etag = item["_etag"]
        session = PlaySession.from_dict(item)

        if session.playerId != player_id:
            raise ForbiddenError()
        if session.status == "concluded":
            raise SessionConcludedError()
        if session.isActiveForPlayer:
            raise AlreadyActiveError()
        self._check_story_available(session)

        session.isActiveForPlayer = True
        self._container().replace_item(
            item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
        )
        self._deactivate_other_active_sessions(player_id, exclude_session_id=session.id)
        return session

    # --- Saved games: list, detail, checkpoints (009-save-and-continue) ---

    def list_player_sessions(self, player_id: str) -> list[dict[str, Any]]:
        """The player's own in-progress games, newest activity first (data-model.md
        "Saved Game Summary"). Adventure names are batch-resolved by distinct
        `adventureId` (research.md Decision 4).

        Backs both the continue screen and the sign-out prompt's active-game check, so
        it is called on every `/game` visit and every sign-out click — a real hot path,
        not an occasional one. Projects only the fields a summary row needs (the latest
        turn via `ARRAY_SLICE`, not the whole `turns` history) rather than reading full
        session documents just to discard almost all of each one."""
        rows = self._cosmos.query(
            config.PLAY_SESSIONS_CONTAINER,
            "SELECT c.id, c.adventureId, c.characterName, c.startedAt, c.lastInteractionAt, "
            "c.isActiveForPlayer, ARRAY_SLICE(c.turns, -1) AS latestTurn, "
            "ARRAY_LENGTH(c.turns) AS turnCount, ARRAY_LENGTH(c.checkpoints) AS checkpointCount "
            "FROM c WHERE c.playerId = @playerId AND c.status = 'active'",
            params=[{"name": "@playerId", "value": player_id}],
        )
        rows.sort(key=lambda row: row["lastInteractionAt"], reverse=True)

        names: dict[str, str] = {}
        available: dict[str, bool] = {}
        for row in rows:
            adventure_id = row["adventureId"]
            if adventure_id not in names:
                names[adventure_id] = self._resolve_adventure_name(adventure_id)
            if adventure_id not in available:
                available[adventure_id] = self._resolve_adventure_available(adventure_id)

        return [
            self._session_summary_from_row(row, names[row["adventureId"]], available[row["adventureId"]])
            for row in rows
        ]

    def delete_active_sessions_for_adventure(self, adventure_id: str) -> int:
        """Cascade for a story delete (025-story-delete FR-004, research.md Decision 2):
        permanently remove every in-progress (`status == 'active'`) session for
        `adventure_id`, regardless of which player owns it. Concluded sessions are left
        untouched — they are history, not "in progress." Returns the count actually
        removed. Idempotent per row: a session that vanishes between the query and its
        own delete (e.g. the player's own next turn racing this cascade, or a second
        concurrent delete attempt) is skipped rather than raising, so one such race
        never 500s the admin delete endpoint after the story itself is already gone."""
        rows = self._cosmos.query(
            config.PLAY_SESSIONS_CONTAINER,
            "SELECT c.id FROM c WHERE c.adventureId = @adventureId AND c.status = 'active'",
            params=[{"name": "@adventureId", "value": adventure_id}],
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

    def get_session_for_player(self, session_id: str, player_id: str) -> PlaySession:
        """The player's own session in full, for rehydrating the play surface
        (data-model.md "Saved Game Detail"). Concluded sessions are readable here — only
        the list excludes them."""
        item = self._read_item(session_id)
        if item is None:
            raise SessionNotFoundError()
        session = PlaySession.from_dict(item)
        if session.playerId != player_id:
            raise ForbiddenError()
        return session

    def get_session_detail_for_player(self, session_id: str, player_id: str) -> dict[str, Any]:
        """The Saved Game Detail shape (data-model.md), including every turn and
        checkpoint — sufficient to rebuild the play surface exactly as the player left it
        (FR-006, contracts/api.md)."""
        session = self.get_session_for_player(session_id, player_id)
        self._check_story_available(session)
        summary = self._session_summary(session, self._resolve_adventure_name(session.adventureId))
        summary["characterType"] = session.characterType
        summary["status"] = session.status
        summary["completionReason"] = session.completionReason
        summary["turns"] = [turn.to_dict() for turn in session.turns]
        summary["checkpoints"] = [checkpoint.to_dict() for checkpoint in session.checkpoints]
        return summary

    def record_checkpoint(self, session_id: str, player_id: str) -> CheckpointMarker:
        """Append a labelled, timestamped marker to the session (data-model.md
        invariants, research.md Decisions 2, 7, 8). Never touches `turns`, `status`,
        `summary`, or `lastInteractionAt`."""
        for _attempt in range(2):
            item = self._read_item(session_id)
            if item is None:
                raise SessionNotFoundError()
            etag = item["_etag"]
            session = PlaySession.from_dict(item)

            if session.playerId != player_id:
                raise ForbiddenError()
            if session.status == "concluded":
                raise SessionConcludedError()

            latest = session.turns[-1] if session.turns else None
            marker = CheckpointMarker(
                label=(latest.locationLabel if latest and latest.locationLabel else DEFAULT_CHECKPOINT_LABEL),
                turnNumber=latest.turnNumber if latest else 0,
                createdAt=_now(),
            )
            session.checkpoints.append(marker)

            try:
                self._container().replace_item(
                    item=session.id,
                    body=session.to_dict(),
                    etag=etag,
                    match_condition=MatchConditions.IfNotModified,
                )
                return marker
            except CosmosAccessConditionFailedError:
                continue

        raise CheckpointUnavailableError()

    def _resolve_adventure_name(self, adventure_id: str) -> str:
        """`"Adventure"` when the story can no longer be read (research.md Decision 4) —
        a player resuming a game they already started must never lose the row over it.
        Uses `get_story_name`'s projected query rather than `get_story`'s full point read,
        since this only ever needs the name (issue #257)."""
        name = self._stories.get_story_name(adventure_id)
        return name if name is not None else "Adventure"

    def _resolve_adventure_available(self, adventure_id: str) -> bool:
        """025-story-delete FR-009/FR-011, research.md Decision 5: `Story.published`,
        read fresh on every call so a re-publish is reflected on the very next list load
        with no separate restore step. Defaults to UNAVAILABLE when the story can no
        longer be read at all — a missing story is exactly the condition
        `_check_story_available` treats as `AdventureNotFoundError` (story_deleted) on
        the very next turn/resume/detail request, so showing the row as available here
        would invite a Resume that is guaranteed to fail; this deliberately differs from
        `_resolve_adventure_name`'s own fallback, since a missing *name* is cosmetic but
        a missing *availability* is misleading."""
        summary = self._stories.get_adventure_summary(adventure_id)
        return summary["published"] if summary is not None else False

    @staticmethod
    def _session_summary(session: PlaySession, adventure_name: str) -> dict[str, Any]:
        latest = session.turns[-1] if session.turns else None
        return {
            "sessionId": session.id,
            "adventureId": session.adventureId,
            "adventureName": adventure_name,
            "characterName": session.characterName,
            "locationLabel": latest.locationLabel if latest else None,
            "progress": latest.progress if latest else None,
            "turnCount": len(session.turns),
            "startedAt": session.startedAt,
            "lastInteractionAt": session.lastInteractionAt,
            "isActiveForPlayer": session.isActiveForPlayer,
            "checkpointCount": len(session.checkpoints),
        }

    @staticmethod
    def _session_summary_from_row(row: dict[str, Any], adventure_name: str, available: bool) -> dict[str, Any]:
        """Same shape as `_session_summary`, but built from a projected `list_player_sessions`
        row instead of a full `PlaySession` (no `turns` to slice — Cosmos already did).
        `available` (025-story-delete FR-009) is computed live from the story's current
        `published` state, never stored on the session itself."""
        latest_turns = row.get("latestTurn") or []
        latest = latest_turns[0] if latest_turns else None
        return {
            "sessionId": row["id"],
            "adventureId": row["adventureId"],
            "adventureName": adventure_name,
            "characterName": row["characterName"],
            "locationLabel": latest.get("locationLabel") if latest else None,
            "progress": latest.get("progress") if latest else None,
            "turnCount": row.get("turnCount") or 0,
            "startedAt": row["startedAt"],
            "lastInteractionAt": row["lastInteractionAt"],
            "isActiveForPlayer": row["isActiveForPlayer"],
            "checkpointCount": row.get("checkpointCount") or 0,
            "available": available,
        }

    # --- Helpers ---

    def _most_recent_session_start(self, player_id: str) -> Optional[str]:
        """When this player last started a session, from the same cross-partition query
        shape session deactivation already relies on — no new stored state needed."""
        rows = self._cosmos.query(
            config.PLAY_SESSIONS_CONTAINER,
            "SELECT c.startedAt FROM c WHERE c.playerId = @playerId",
            params=[{"name": "@playerId", "value": player_id}],
        )
        starts = [row["startedAt"] for row in rows if row.get("startedAt")]
        return max(starts) if starts else None

    def _deactivate_other_active_sessions(self, player_id: str, exclude_session_id: str) -> None:
        rows = self._cosmos.query(
            config.PLAY_SESSIONS_CONTAINER,
            "SELECT * FROM c WHERE c.playerId = @playerId AND c.status = 'active' "
            "AND c.isActiveForPlayer = true AND c.id != @excludeId",
            params=[
                {"name": "@playerId", "value": player_id},
                {"name": "@excludeId", "value": exclude_session_id},
            ],
        )
        container = self._container()
        for row in rows:
            # As in _release_claim: write the model's own shape, never the query result,
            # which carries Cosmos system metadata alongside the document's fields.
            other = PlaySession.from_dict(row)
            other.isActiveForPlayer = False
            try:
                container.replace_item(
                    item=other.id,
                    body=other.to_dict(),
                    etag=row["_etag"],
                    match_condition=MatchConditions.IfNotModified,
                )
            except CosmosAccessConditionFailedError:
                logger.warning("Concurrent deactivate for session %s; skipping", other.id)

    def _duration_ceiling_reached(self, story, session: PlaySession) -> bool:
        max_minutes = story.completionCriteria.maxDurationMinutes
        if not max_minutes:
            return False
        elapsed_minutes = (_now_dt() - _parse(session.startedAt)).total_seconds() / 60
        return elapsed_minutes >= max_minutes

    def _evaluate_completion(self, story, session: PlaySession, turn_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        criteria = story.completionCriteria
        newly_success = turn_data.get("newlySatisfiedSuccessConditions", [])
        newly_failure = turn_data.get("newlySatisfiedFailureConditions", [])

        session.satisfiedSuccessConditions = sorted(set(session.satisfiedSuccessConditions) | set(newly_success))
        session.satisfiedFailureConditions = sorted(set(session.satisfiedFailureConditions) | set(newly_failure))

        success_ends = self._rule_satisfied(criteria.successConditions, session.satisfiedSuccessConditions, criteria.rule)
        failure_ends = self._rule_satisfied(criteria.failureConditions, session.satisfiedFailureConditions, criteria.rule)

        # Success is checked first: a same-turn tie is decided in success's favor (FR-009).
        if success_ends:
            detail_index = newly_success[0] if newly_success else session.satisfiedSuccessConditions[0]
            return {"type": "success", "detail": criteria.successConditions[detail_index]}
        if failure_ends:
            detail_index = newly_failure[0] if newly_failure else session.satisfiedFailureConditions[0]
            return {"type": "failure", "detail": criteria.failureConditions[detail_index]}
        return None

    @staticmethod
    def _rule_satisfied(configured: list[str], satisfied_indices: list[int], rule: Optional[str]) -> bool:
        if not configured:
            return False
        if rule == "all":
            return set(range(len(configured))) <= set(satisfied_indices)
        return len(satisfied_indices) > 0

    def _deflection_turn_data(self, session: PlaySession, standing: PlayerContentSafetyStanding) -> dict[str, Any]:
        text = "That doesn't seem to work here."
        if standing.lockoutUntil is not None:
            text += f" A few of your messages were blocked, so play is paused for a bit. {describe_lockout(standing.lockoutUntil)}"
        last_turn = session.turns[-1] if session.turns else None
        return {
            "narrativeText": text,
            "suggestedActions": ["look around", "wait", "think"],
            "locationLabel": last_turn.locationLabel if last_turn else "Unknown",
            "goalLabel": last_turn.goalLabel if last_turn else None,
            "progress": last_turn.progress if last_turn else None,
            "newlySatisfiedSuccessConditions": [],
            "newlySatisfiedFailureConditions": [],
        }

    @staticmethod
    def _turn_from_llm_data(
        turn_number: int, player_input: Optional[str], turn_data: dict[str, Any], timestamp: str
    ) -> PlayerInteraction:
        return PlayerInteraction(
            turnNumber=turn_number,
            playerInput=player_input,
            narrativeText=turn_data["narrativeText"],
            suggestedActions=turn_data["suggestedActions"],
            locationLabel=turn_data["locationLabel"],
            goalLabel=turn_data.get("goalLabel"),
            progress=turn_data.get("progress"),
            timestamp=timestamp,
        )
