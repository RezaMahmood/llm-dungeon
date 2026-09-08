"""Unit tests for TestPlaySessionService (010-story-test-play). Cosmos and LLMService are
faked/mocked in-memory, matching this repo's other unit tests.

T010-T013 all write to this one file, so they run sequentially with respect to each other
(tasks.md)."""

from __future__ import annotations

import datetime
import uuid
from unittest.mock import MagicMock

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.llm_service import LLMContentFilteredError
from backend.services.story_service import StoryService
from backend.services.test_play_session_service import (
    ForbiddenError,
    InteractionInProgressError,
    InvalidInputError,
    NarrativeUnavailableError,
    RateLimitedError,
    SessionConcludedError,
    SessionNotFoundError,
    StoryNotFoundError,
    TestPlaySessionService,
)

ADMIN_ID = "admin-oid-1"
OTHER_ADMIN_ID = "admin-oid-2"


class FakeContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self._etag_counter = 0

    def _next_etag(self) -> str:
        self._etag_counter += 1
        return f"etag-{self._etag_counter}"

    def read_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        return self.items[item]

    def create_item(self, body):
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[body["id"]] = body
        return body

    def upsert_item(self, body):
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[body["id"]] = body
        return body

    def replace_item(self, item, body, etag=None, match_condition=None):
        current = self.items.get(item)
        if match_condition == MatchConditions.IfNotModified and current is not None and current.get("_etag") != etag:
            raise CosmosAccessConditionFailedError
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[item] = body
        return body

    def delete_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        del self.items[item]


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        return list(self.get_container(container_name).items.values())


OPENING_TURN_DATA = {
    "narrativeText": "The lighthouse door creaks open.",
    "suggestedActions": ["look around", "step inside"],
    "locationLabel": "Lighthouse entrance",
    "goalLabel": None,
    "progress": None,
    "newlySatisfiedSuccessConditions": [],
    "newlySatisfiedFailureConditions": [],
}


def _turn_data(text="You look around.", success=None, failure=None) -> dict:
    return {
        "narrativeText": text,
        "suggestedActions": ["look", "listen", "wait"],
        "locationLabel": "The cove",
        "goalLabel": "Find the keeper",
        "progress": None,
        "newlySatisfiedSuccessConditions": success or [],
        "newlySatisfiedFailureConditions": failure or [],
    }


def _story(**overrides) -> Story:
    defaults = dict(
        id=str(uuid.uuid4()),
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A half-abandoned lighthouse on a foggy cove.",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-09-05T00:00:00Z",
        contentUpdatedAt="2026-09-05T00:00:00Z",
        published=False,
    )
    defaults.update(overrides)
    return Story(**defaults)


def _service(story: Story, llm_turn_data=OPENING_TURN_DATA, cosmos: FakeCosmosService | None = None):
    cosmos = cosmos or FakeCosmosService()
    cosmos.get_container(config.STORIES_CONTAINER).upsert_item(story.to_dict())
    llm = MagicMock()
    if isinstance(llm_turn_data, list):
        llm.generate_gameplay_turn.side_effect = llm_turn_data
    else:
        llm.generate_gameplay_turn.return_value = llm_turn_data
    stories = StoryService(cosmos_service=cosmos)
    service = TestPlaySessionService(cosmos_service=cosmos, story_service=stories, llm_service=llm)
    return service, cosmos, llm, stories


def _clear_rate_limit(cosmos: FakeCosmosService, session_id: str) -> None:
    container = cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    container.items[session_id]["lastInteractionAt"] = past


# --- create_session (T010, FR-001, FR-002) ---


def test_create_session_works_against_a_draft_story():
    story = _story(published=False)
    service, _cosmos, llm, _stories = _service(story)

    session = service.create_session(story.id, ADMIN_ID)

    assert session.storyId == story.id
    assert session.administratorId == ADMIN_ID
    assert session.characterType == "Curious Cousin"
    assert session.characterName == "Tester"
    assert session.turns[0].turnNumber == 0
    assert session.turns[0].playerInput is None
    llm.generate_gameplay_turn.assert_called_once_with(story, session, None)


def test_create_session_raises_story_not_found_for_missing_story():
    service, _cosmos, _llm, _stories = _service(_story())

    try:
        service.create_session("missing", ADMIN_ID)
        assert False, "expected StoryNotFoundError"
    except StoryNotFoundError:
        pass


def test_create_session_turn_zero_does_not_stamp_last_test_played_at():
    story = _story()
    service, cosmos, _llm, stories = _service(story)

    service.create_session(story.id, ADMIN_ID)

    persisted = stories.get_story(story.id)
    assert persisted.lastTestPlayedAt is None


# --- submit_exchange completion triggering (T011, FR-004, FR-006) ---


def test_submit_exchange_concludes_session_on_newly_satisfied_success_condition():
    story = _story()
    service, cosmos, _llm, _stories = _service(story, llm_turn_data=[OPENING_TURN_DATA, _turn_data(success=[0])])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)

    updated, completion_reason = service.submit_exchange(session.id, ADMIN_ID, "search for the keeper")

    assert updated.status == "concluded"
    assert completion_reason == {"type": "success", "detail": "Find the keeper"}


def test_submit_exchange_stays_active_with_no_newly_satisfied_conditions():
    story = _story()
    service, cosmos, _llm, _stories = _service(story, llm_turn_data=[OPENING_TURN_DATA, _turn_data()])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)

    updated, completion_reason = service.submit_exchange(session.id, ADMIN_ID, "look around")

    assert updated.status == "active"
    assert completion_reason is None


# --- abort/delete (T012, FR-005, FR-010) ---


def test_delete_session_removes_the_document_but_preserves_last_test_played_at():
    story = _story()
    service, cosmos, _llm, stories = _service(story, llm_turn_data=[OPENING_TURN_DATA, _turn_data(success=[0])])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)
    service.submit_exchange(session.id, ADMIN_ID, "search for the keeper")

    service.delete_session(session.id, ADMIN_ID)

    assert session.id not in cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER).items
    persisted_story = stories.get_story(story.id)
    assert persisted_story.lastTestPlayedAt is not None


def test_delete_session_is_idempotent_for_a_vanished_session():
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    service.delete_session("never-existed", ADMIN_ID)  # must not raise


def test_delete_session_rejects_another_administrators_session():
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    session = service.create_session(story.id, ADMIN_ID)

    try:
        service.delete_session(session.id, OTHER_ADMIN_ID)
        assert False, "expected ForbiddenError"
    except ForbiddenError:
        pass


# --- isolation (T013, FR-009) ---


def test_get_session_rejects_another_administrators_session():
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    session = service.create_session(story.id, ADMIN_ID)

    try:
        service.get_session(session.id, OTHER_ADMIN_ID)
        assert False, "expected ForbiddenError"
    except ForbiddenError:
        pass


def test_get_session_raises_not_found_for_missing_session():
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    try:
        service.get_session("missing", ADMIN_ID)
        assert False, "expected SessionNotFoundError"
    except SessionNotFoundError:
        pass


def test_two_administrators_testing_the_same_story_concurrently_get_independent_sessions():
    story = _story()
    service, cosmos, llm, _stories = _service(
        story, llm_turn_data=[OPENING_TURN_DATA, OPENING_TURN_DATA, _turn_data(success=[0]), _turn_data()]
    )

    session_a = service.create_session(story.id, ADMIN_ID)
    session_b = service.create_session(story.id, OTHER_ADMIN_ID)

    assert session_a.id != session_b.id

    _clear_rate_limit(cosmos, session_a.id)
    _clear_rate_limit(cosmos, session_b.id)
    updated_a, reason_a = service.submit_exchange(session_a.id, ADMIN_ID, "search for the keeper")
    updated_b, reason_b = service.submit_exchange(session_b.id, OTHER_ADMIN_ID, "look around")

    assert updated_a.status == "concluded"
    assert updated_b.status == "active"
    assert reason_a is not None
    assert reason_b is None
    # Neither administrator can reach the other's session.
    assert service.get_session(session_a.id, ADMIN_ID).id == session_a.id
    try:
        service.get_session(session_a.id, OTHER_ADMIN_ID)
        assert False, "expected ForbiddenError"
    except ForbiddenError:
        pass


def test_no_test_play_write_reaches_play_sessions_or_safety_standings_containers():
    story = _story()
    service, cosmos, _llm, _stories = _service(story, llm_turn_data=[OPENING_TURN_DATA, _turn_data()])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)
    service.submit_exchange(session.id, ADMIN_ID, "look around")

    assert cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).items == {}
    assert cosmos.get_container(config.PLAYER_CONTENT_SAFETY_STANDINGS_CONTAINER).items == {}


# --- validation, rate limiting, single-flight, content safety (T019-T021) ---


def test_submit_exchange_rejects_empty_input():
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)

    try:
        service.submit_exchange(session.id, ADMIN_ID, "   ")
        assert False, "expected InvalidInputError"
    except InvalidInputError:
        pass


def test_submit_exchange_enforces_the_interaction_interval():
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    session = service.create_session(story.id, ADMIN_ID)

    try:
        service.submit_exchange(session.id, ADMIN_ID, "look around")
        assert False, "expected RateLimitedError"
    except RateLimitedError:
        pass


def test_submit_exchange_rejects_a_concluded_session():
    story = _story()
    service, cosmos, _llm, _stories = _service(story, llm_turn_data=[OPENING_TURN_DATA, _turn_data(success=[0])])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)
    service.submit_exchange(session.id, ADMIN_ID, "search for the keeper")
    _clear_rate_limit(cosmos, session.id)

    try:
        service.submit_exchange(session.id, ADMIN_ID, "keep going")
        assert False, "expected SessionConcludedError"
    except SessionConcludedError:
        pass


def test_submit_exchange_rejects_a_claim_already_in_progress():
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)
    container = cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER)
    container.items[session.id]["interactionInProgress"] = True

    try:
        service.submit_exchange(session.id, ADMIN_ID, "look around")
        assert False, "expected InteractionInProgressError"
    except InteractionInProgressError:
        pass


def test_submit_exchange_content_filtered_returns_deflection_without_recording_a_flag():
    story = _story()
    service, cosmos, llm, _stories = _service(story, llm_turn_data=[OPENING_TURN_DATA])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)
    llm.generate_gameplay_turn.side_effect = LLMContentFilteredError("filtered")

    updated, completion_reason = service.submit_exchange(session.id, ADMIN_ID, "say something unsafe")

    assert completion_reason is None
    assert updated.turns[-1].narrativeText == "That doesn't seem to work here."
    assert cosmos.get_container(config.PLAYER_CONTENT_SAFETY_STANDINGS_CONTAINER).items == {}


def test_submit_exchange_maps_llm_output_error_to_narrative_unavailable():
    from backend.services.llm_service import LLMOutputError

    story = _story()
    service, cosmos, llm, _stories = _service(story, llm_turn_data=[OPENING_TURN_DATA])
    session = service.create_session(story.id, ADMIN_ID)
    _clear_rate_limit(cosmos, session.id)
    llm.generate_gameplay_turn.side_effect = LLMOutputError("bad output")

    try:
        service.submit_exchange(session.id, ADMIN_ID, "look around")
        assert False, "expected NarrativeUnavailableError"
    except NarrativeUnavailableError:
        pass
