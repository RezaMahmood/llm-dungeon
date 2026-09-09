"""TestPlaySessionService — an administrator's interactive test playthrough of a draft
story (010-story-test-play research.md, data-model.md). Reuses `LLMService.generate_gameplay_turn()`
for turns 1+ and `StoryService.ensure_starting_point()`/`story.startingPoint` for turn 0,
plus the shared `completion_rules` module, rather than the player session lifecycle: no
`published` gate, no per-player exclusivity, no content-safety accrual against the
administrator (research.md Decisions 2-4)."""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Optional

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.models.test_play_session import TestPlayExchange, TestPlaySession
from backend.services import completion_rules
from backend.services.cosmos_service import CosmosService, shared_cosmos_service
from backend.services.llm_service import LLMContentFilteredError, LLMOutputError, LLMRateLimitError, LLMService
from backend.services.story_service import (
    ContentGenerationFailedError,
    ContentGenerationRateLimitedError,
    StoryService,
)
from backend.services.story_service import StoryNotFoundError as StoryServiceStoryNotFoundError

logger = logging.getLogger("test_play_session_service")

# Mirrors PlaySessionService's per-session interaction floor (research.md Decision 3) —
# per-player throttles (MIN_SESSION_CREATION_INTERVAL_SECONDS, content-safety lockout) are
# deliberately not reused, each an FR-009 interference vector.
MIN_INTERACTION_INTERVAL_SECONDS = 2

# Fixed literal (research.md Decision 6) — no character-setup step exists for test play.
TESTER_CHARACTER_NAME = "Tester"

# Mirrors PlaySessionService's REDACTED_PLAYER_INPUT: a filtered submission is never stored
# verbatim, since `turns[].playerInput` is replayed into the prompt for every later turn.
REDACTED_PLAYER_INPUT = "[removed by content safety]"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_dt() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


# --- Errors — the API layer (api/admin/test_play.py) maps each to its contracts/api.md shape ---


class StoryNotFoundError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class SessionConcludedError(Exception):
    pass


class InteractionInProgressError(Exception):
    pass


class RateLimitedError(Exception):
    pass


class InvalidInputError(Exception):
    pass


class NarrativeUnavailableError(Exception):
    pass


class TestPlaySessionService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        story_service: Optional[StoryService] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        self._cosmos = cosmos_service or shared_cosmos_service()
        self._stories = story_service or StoryService(cosmos_service=self._cosmos)
        self._llm = llm_service or LLMService()

    def _container(self):
        return self._cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER)

    def _read_item(self, session_id: str) -> Optional[dict[str, Any]]:
        try:
            return self._container().read_item(item=session_id, partition_key=session_id)
        except CosmosResourceNotFoundError:
            return None

    # --- Session creation (T018, FR-001) ---

    def create_session(self, story_id: str, administrator_id: str) -> TestPlaySession:
        """No `published` check — testing a draft is the point. Defaults the character to
        `story.characterTypes[0]` with the fixed name `"Tester"` (research.md Decision 6).
        No qualifying exchange occurs here, so `Story.lastTestPlayedAt` is not written
        (research.md Decision 9). Turn 0 replays the story's persisted `startingPoint`
        verbatim rather than generating a fresh opening narrative per session — the same
        fix #279 applied to `PlaySessionService`, since a live per-session LLM call here
        is exactly as unreliable and unnecessary for testing as it was for real play."""
        story = self._stories.get_story(story_id)
        if story is None:
            raise StoryNotFoundError()

        try:
            story = self._stories.ensure_starting_point(story)
        except StoryServiceStoryNotFoundError as exc:
            # The story was deleted between the read above and the backfill write.
            raise StoryNotFoundError() from exc
        except (ContentGenerationFailedError, ContentGenerationRateLimitedError) as exc:
            # Only reachable for a story persisted before `startingPoint` existed (#271).
            logger.warning("Starting-point backfill failed for story %s", story.id, exc_info=exc)
            raise NarrativeUnavailableError() from exc

        now = _now()
        session = TestPlaySession(
            id=str(uuid.uuid4()),
            storyId=story.id,
            administratorId=administrator_id,
            characterName=TESTER_CHARACTER_NAME,
            characterType=story.characterTypes[0].name,
            startedAt=now,
            lastInteractionAt=now,
        )

        session.turns.append(self._turn_from_llm_data(0, None, story.startingPoint.to_dict(), now))
        self._container().create_item(session.to_dict())
        logger.info("Test-play session created", extra={"session_id": session.id, "story_id": story_id})
        return session

    # --- Interaction submission (T019, T020, T021, FR-002, FR-004) ---

    def submit_exchange(self, session_id: str, administrator_id: str, raw_input: str) -> tuple[TestPlaySession, Optional[dict]]:
        trimmed_input = (raw_input or "").strip()
        if not trimmed_input:
            raise InvalidInputError()

        item = self._read_item(session_id)
        if item is None:
            raise SessionNotFoundError()
        etag = item["_etag"]
        session = TestPlaySession.from_dict(item)

        if session.administratorId != administrator_id:
            raise ForbiddenError()
        if session.status == "concluded":
            raise SessionConcludedError()
        if (_now_dt() - _parse(session.lastInteractionAt)).total_seconds() < MIN_INTERACTION_INTERVAL_SECONDS:
            raise RateLimitedError()
        if session.interactionInProgress:
            raise InteractionInProgressError()

        story = self._stories.get_story(session.storyId)
        if story is None:
            raise StoryNotFoundError()

        session.interactionInProgress = True
        try:
            claimed = self._container().replace_item(
                item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
            )
        except CosmosAccessConditionFailedError as exc:
            raise InteractionInProgressError() from exc

        try:
            return self._generate_and_persist_turn(story, session, trimmed_input, claimed["_etag"])
        except Exception:
            self._release_claim(session.id)
            raise

    def _generate_and_persist_turn(
        self, story, session: TestPlaySession, trimmed_input: str, etag: str
    ) -> tuple[TestPlaySession, Optional[dict]]:
        now = _now()

        try:
            turn_data = self._llm.generate_gameplay_turn(story, session, trimmed_input)
            turn = self._turn_from_llm_data(len(session.turns), trimmed_input, turn_data, now)
            completion_reason = completion_rules.evaluate_completion(story, session, turn_data)
        except LLMContentFilteredError:
            # T021: the in-fiction deflection turn is returned, but no safety flag is
            # recorded and no lockout is enforced — testing a story must never accrue
            # against the administrator's own gameplay standing (research.md Decision 4).
            turn_data = self._deflection_turn_data(session)
            turn = self._turn_from_llm_data(len(session.turns), REDACTED_PLAYER_INPUT, turn_data, now)
            completion_reason = None
        except (LLMOutputError, LLMRateLimitError) as exc:
            raise NarrativeUnavailableError() from exc

        session.turns.append(turn)
        session.lastInteractionAt = now
        if completion_reason is not None:
            session.status = "concluded"
            session.completionReason = completion_reason
            session.endedAt = now

        session.interactionInProgress = False
        self._container().replace_item(
            item=session.id, body=session.to_dict(), etag=etag, match_condition=MatchConditions.IfNotModified
        )

        # T020: only a qualifying exchange (playerInput is not None, persisted
        # successfully) stamps the marker — never turn 0, never on session creation
        # (research.md Decision 9). Lives here, not in the route handler, so every
        # caller of this method stamps it.
        self._stories.record_test_play(story.id)

        return session, completion_reason

    def _release_claim(self, session_id: str) -> None:
        try:
            item = self._read_item(session_id)
            if item is None:
                return
            session = TestPlaySession.from_dict(item)
            session.interactionInProgress = False
            self._container().replace_item(
                item=session_id,
                body=session.to_dict(),
                etag=item["_etag"],
                match_condition=MatchConditions.IfNotModified,
            )
        except Exception:  # noqa: BLE001 - must never mask the failure that brought us here
            logger.exception("Could not release the interaction claim on test-play session %s", session_id)

    # --- Delete / get (T022, FR-005, FR-009, FR-010) ---

    def delete_session(self, session_id: str, administrator_id: str) -> None:
        """Idempotent per document (FR-005) — a session that vanishes between read and
        delete is treated as already deleted. Never clears `Story.lastTestPlayedAt`
        (FR-010): the marker lives on the Story, not the session."""
        item = self._read_item(session_id)
        if item is None:
            return
        session = TestPlaySession.from_dict(item)
        if session.administratorId != administrator_id:
            raise ForbiddenError()
        try:
            self._container().delete_item(item=session_id, partition_key=session_id)
        except CosmosResourceNotFoundError:
            pass

    def get_session(self, session_id: str, administrator_id: str) -> TestPlaySession:
        item = self._read_item(session_id)
        if item is None:
            raise SessionNotFoundError()
        session = TestPlaySession.from_dict(item)
        if session.administratorId != administrator_id:
            raise ForbiddenError()
        return session

    # --- Helpers ---

    def _deflection_turn_data(self, session: TestPlaySession) -> dict[str, Any]:
        last_turn = session.turns[-1] if session.turns else None
        return {
            "narrativeText": "That doesn't seem to work here.",
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
    ) -> TestPlayExchange:
        return TestPlayExchange(
            turnNumber=turn_number,
            playerInput=player_input,
            narrativeText=turn_data["narrativeText"],
            suggestedActions=turn_data["suggestedActions"],
            locationLabel=turn_data["locationLabel"],
            goalLabel=turn_data.get("goalLabel"),
            progress=turn_data.get("progress"),
            timestamp=timestamp,
        )
