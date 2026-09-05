"""PlaySessionService — session lifecycle (creation, interaction submission, resume),
cross-player and per-player (FR-015) exclusivity, rate limiting, content-safety lockout
enforcement, completion-rule evaluation, and 20-turn summarization
(008-core-gameplay research.md, data-model.md)."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Optional

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.models.play_session import PlayerInteraction, PlaySession
from backend.models.player_content_safety_standing import PlayerContentSafetyStanding
from backend.services.cosmos_service import CosmosService
from backend.services.llm_service import LLMContentFilteredError, LLMOutputError, LLMRateLimitError, LLMService
from backend.services.player_content_safety_standing_service import PlayerContentSafetyStandingService
from backend.services.story_service import StoryService

logger = logging.getLogger("play_session_service")

MAX_CHARACTER_NAME_LENGTH = 50
# Well above real typing/round-trip time, well below anything a legitimate player would
# hit (research.md Decision 4) — a best-effort, request-shape limiter, not a distributed
# rate-limiter.
MIN_INTERACTION_INTERVAL_SECONDS = 2
SUMMARIZE_EVERY_N_TURNS = 20

FIELD_MESSAGES = {
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

        session.interactionInProgress = True
        try:
            claimed = self._container().replace_item(
                item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
            )
        except CosmosAccessConditionFailedError as exc:
            raise InteractionInProgressError() from exc
        etag = claimed["_etag"]

        story = self._stories.get_story(session.adventureId)
        now = _now()
        completion_reason: Optional[dict[str, Any]] = None

        if self._duration_ceiling_reached(story, session):
            try:
                turn_data = self._llm.generate_gameplay_turn(
                    story,
                    session,
                    f"{trimmed_input} (Note to narrator: this session's time has run out — narrate a concluding scene now.)",
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
                turn = self._turn_from_llm_data(len(session.turns), trimmed_input, turn_data, now)
            except (LLMOutputError, LLMRateLimitError) as exc:
                raise NarrativeUnavailableError() from exc

        session.turns.append(turn)
        session.lastInteractionAt = now
        if completion_reason is not None:
            session.status = "concluded"
            session.completionReason = completion_reason
            session.endedAt = now

        if len(session.turns) % SUMMARIZE_EVERY_N_TURNS == 0 and len(session.turns) > session.summarizedThroughTurn:
            session.summary = self._llm.summarize_session_history(story, session)
            session.summarizedThroughTurn = len(session.turns)

        session.interactionInProgress = False
        self._container().replace_item(
            item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
        )
        return session, completion_reason

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

        session.isActiveForPlayer = True
        self._container().replace_item(
            item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
        )
        self._deactivate_other_active_sessions(player_id, exclude_session_id=session.id)
        return session

    # --- Helpers ---

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
            row["isActiveForPlayer"] = False
            try:
                container.replace_item(
                    item=row["id"], body=row, etag=row["_etag"], match_condition=MatchConditions.IfNotModified
                )
            except CosmosAccessConditionFailedError:
                logger.warning("Concurrent deactivate for session %s; skipping", row["id"])

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
            text += (
                f" You're temporarily locked out due to repeated flagged submissions. "
                f"Try again after {standing.lockoutUntil}."
            )
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
