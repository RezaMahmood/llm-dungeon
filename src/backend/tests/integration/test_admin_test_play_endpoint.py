"""Integration tests for the four test-play routes (010-story-test-play, contracts/api.md):
status codes, `authorize_admin` enforcement, the full error table, and that a successful
exchange stamps `Story.lastTestPlayedAt`."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.admin.test_play import (
    delete_test_play_session,
    get_test_play_session,
    start_test_play,
    submit_test_play_interaction,
)
from backend.config import config
from backend.models.story import CharacterType, CompletionCriteria, StartingPoint, Story
from backend.services.story_service import StoryService
from backend.services.test_play_session_service import TestPlaySessionService

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_ADMIN_OID = "660e8400-e29b-41d4-a716-446655440111"


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
        from azure.core import MatchConditions  # noqa: F401

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
        from azure.core import MatchConditions
        from azure.cosmos.exceptions import CosmosAccessConditionFailedError

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


STARTING_POINT = StartingPoint(
    narrativeText="The lighthouse door creaks open.",
    suggestedActions=["look around", "step inside"],
    locationLabel="Lighthouse entrance",
)


def _turn_data(success=None) -> dict:
    return {
        "narrativeText": "You look around.",
        "suggestedActions": ["look", "listen", "wait"],
        "locationLabel": "The cove",
        "goalLabel": "Find the keeper",
        "progress": None,
        "newlySatisfiedSuccessConditions": success or [],
        "newlySatisfiedFailureConditions": [],
    }


def _story(**overrides) -> Story:
    defaults = dict(
        id=str(uuid.uuid4()),
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A half-abandoned lighthouse on a foggy cove.",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        narrativeGuidance="Keep it eerie but safe.",
        startingPoint=STARTING_POINT,
        createdBy="admin-oid",
        createdAt="2026-09-05T00:00:00Z",
        contentUpdatedAt="2026-09-05T00:00:00Z",
        published=False,
    )
    defaults.update(overrides)
    return Story(**defaults)


def _service(story: Story, llm_turn_data=None):
    cosmos = FakeCosmosService()
    cosmos.get_container(config.STORIES_CONTAINER).upsert_item(story.to_dict())
    llm = MagicMock()
    if isinstance(llm_turn_data, list):
        llm.generate_gameplay_turn.side_effect = llm_turn_data
    else:
        llm.generate_gameplay_turn.return_value = llm_turn_data if llm_turn_data is not None else _turn_data()
    llm.generate_starting_point.return_value = STARTING_POINT.to_dict()
    stories = StoryService(cosmos_service=cosmos, llm_service=llm)
    service = TestPlaySessionService(cosmos_service=cosmos, story_service=stories, llm_service=llm)
    return service, cosmos, llm, stories


def _patched_authorize_admin(oid: str = ADMIN_OID):
    return patch("backend.api.admin.test_play.authorize_admin", return_value=(True, oid, None))


def _clear_rate_limit(cosmos: FakeCosmosService, session_id: str) -> None:
    import datetime

    container = cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    container.items[session_id]["lastInteractionAt"] = past


def _start(request_factory, service, story_id, oid=ADMIN_OID):
    req = request_factory(
        method="POST",
        url=f"/api/manage/stories/{story_id}/test-play",
        token="valid-token",
        route_params={"storyId": story_id},
    )
    with _patched_authorize_admin(oid):
        return start_test_play(req, test_play_session_service=service)


def _submit(request_factory, service, session_id, body, oid=ADMIN_OID):
    req = request_factory(
        method="POST",
        url=f"/api/manage/test-play-sessions/{session_id}/interactions",
        token="valid-token",
        body=json.dumps(body).encode(),
        route_params={"sessionId": session_id},
    )
    with _patched_authorize_admin(oid):
        return submit_test_play_interaction(req, test_play_session_service=service)


def _delete(request_factory, service, session_id, oid=ADMIN_OID):
    req = request_factory(
        method="DELETE",
        url=f"/api/manage/test-play-sessions/{session_id}",
        token="valid-token",
        route_params={"sessionId": session_id},
    )
    with _patched_authorize_admin(oid):
        return delete_test_play_session(req, test_play_session_service=service)


def _get(request_factory, service, session_id, oid=ADMIN_OID):
    req = request_factory(
        method="GET",
        url=f"/api/manage/test-play-sessions/{session_id}",
        token="valid-token",
        route_params={"sessionId": session_id},
    )
    with _patched_authorize_admin(oid):
        return get_test_play_session(req, test_play_session_service=service)


# --- POST /api/manage/stories/{storyId}/test-play ---


def test_start_test_play_returns_201_with_opening_narrative(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    response = _start(request_factory, service, story.id)

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["narrative"]["turnNumber"] == 0
    assert body["characterType"] == "Curious Cousin"
    assert "sessionId" in body


def test_start_test_play_works_on_an_unpublished_story(request_factory):
    story = _story(published=False)
    service, _cosmos, _llm, _stories = _service(story)

    response = _start(request_factory, service, story.id)

    assert response.status_code == 201


def test_start_test_play_returns_404_for_missing_story(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    response = _start(request_factory, service, "missing")

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_start_test_play_rejects_unauthenticated_request(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    req = request_factory(
        method="POST",
        url=f"/api/manage/stories/{story.id}/test-play",
        route_params={"storyId": story.id},
    )
    response = start_test_play(req, test_play_session_service=service)

    assert response.status_code in (401, 403)


# --- POST /api/manage/test-play-sessions/{sessionId}/interactions ---


def test_submit_interaction_returns_200_and_stamps_last_test_played_at(request_factory):
    story = _story()
    service, cosmos, _llm, stories = _service(story, llm_turn_data=_turn_data())
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)

    response = _submit(request_factory, service, session_id, {"input": "look around"})

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "active"
    persisted = stories.get_story(story.id)
    assert persisted.lastTestPlayedAt is not None


def test_submit_interaction_returns_completion_reason_when_concluded(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story, llm_turn_data=_turn_data(success=[0]))
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)

    response = _submit(request_factory, service, session_id, {"input": "search for the keeper"})

    body = json.loads(response.get_body())
    assert body["status"] == "concluded"
    assert body["completionReason"] == {"type": "success", "detail": "Find the keeper"}


def test_submit_interaction_rejects_empty_input(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)

    response = _submit(request_factory, service, session_id, {"input": "   "})

    assert response.status_code == 400
    assert json.loads(response.get_body())["error"] == "invalid_input"


def test_submit_interaction_rejects_another_administrators_session(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)

    response = _submit(request_factory, service, session_id, {"input": "look around"}, oid=OTHER_ADMIN_OID)

    assert response.status_code == 403
    assert json.loads(response.get_body())["error"] == "access_denied"


def test_submit_interaction_returns_404_for_missing_session(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    response = _submit(request_factory, service, "missing", {"input": "look around"})

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_submit_interaction_rejects_concluded_session(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story, llm_turn_data=_turn_data(success=[0]))
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)
    _submit(request_factory, service, session_id, {"input": "search for the keeper"})
    _clear_rate_limit(cosmos, session_id)

    response = _submit(request_factory, service, session_id, {"input": "keep going"})

    assert response.status_code == 409
    assert json.loads(response.get_body())["error"] == "session_concluded"


def test_submit_interaction_rejects_a_claim_already_in_progress(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)
    cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER).items[session_id]["interactionInProgress"] = True

    response = _submit(request_factory, service, session_id, {"input": "look around"})

    assert response.status_code == 409
    assert json.loads(response.get_body())["error"] == "interaction_in_progress"


def test_submit_interaction_is_rate_limited_within_the_interval(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]

    response = _submit(request_factory, service, session_id, {"input": "look around"})

    assert response.status_code == 429
    assert json.loads(response.get_body())["error"] == "rate_limited"


def test_submit_interaction_rejects_unauthenticated_request(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)

    req = request_factory(
        method="POST",
        url=f"/api/manage/test-play-sessions/{session_id}/interactions",
        body=json.dumps({"input": "look around"}).encode(),
        route_params={"sessionId": session_id},
    )
    response = submit_test_play_interaction(req, test_play_session_service=service)

    assert response.status_code in (401, 403)


# --- DELETE /api/manage/test-play-sessions/{sessionId} ---


def test_delete_session_returns_200_and_deletes_the_document(request_factory):
    story = _story()
    service, cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]

    response = _delete(request_factory, service, session_id)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"status": "deleted", "sessionId": session_id}
    assert session_id not in cosmos.get_container(config.TEST_PLAY_SESSIONS_CONTAINER).items


def test_delete_session_is_idempotent_for_a_vanished_session(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    response = _delete(request_factory, service, "never-existed")

    assert response.status_code == 200


def test_delete_session_rejects_another_administrators_session(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]

    response = _delete(request_factory, service, session_id, oid=OTHER_ADMIN_OID)

    assert response.status_code == 403
    assert json.loads(response.get_body())["error"] == "access_denied"


def test_delete_session_does_not_reset_last_test_played_at(request_factory):
    story = _story()
    service, cosmos, _llm, stories = _service(story, llm_turn_data=_turn_data())
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]
    _clear_rate_limit(cosmos, session_id)
    _submit(request_factory, service, session_id, {"input": "look around"})

    _delete(request_factory, service, session_id)

    persisted = stories.get_story(story.id)
    assert persisted.lastTestPlayedAt is not None


# --- GET /api/manage/test-play-sessions/{sessionId} ---


def test_get_session_returns_full_turn_history(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]

    response = _get(request_factory, service, session_id)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["session"]["id"] == session_id
    assert len(body["session"]["turns"]) == 1


def test_get_session_rejects_another_administrators_session(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)
    start_response = _start(request_factory, service, story.id)
    session_id = json.loads(start_response.get_body())["sessionId"]

    response = _get(request_factory, service, session_id, oid=OTHER_ADMIN_OID)

    assert response.status_code == 403
    assert json.loads(response.get_body())["error"] == "access_denied"


def test_get_session_returns_404_for_missing_session(request_factory):
    story = _story()
    service, _cosmos, _llm, _stories = _service(story)

    response = _get(request_factory, service, "missing")

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"
