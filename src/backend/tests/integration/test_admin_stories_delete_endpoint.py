"""Integration tests for DELETE /api/manage/stories/{storyId} (025-story-delete,
contracts/api.md, spec.md Edge Cases, SC-001). Cosmos is faked in-memory, following the
FakeCosmosService pattern in test_admin_stories_publish_endpoint.py. Also covers the
delete cascade against PlaySession (FR-004) via HTTP (quickstart.md Scenario 4)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.admin.stories import delete_story, get_story
from backend.config import config
from backend.models.play_session import PlayerInteraction, PlaySession
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.play_session_service import PlaySessionService
from backend.services.story_service import StoryService

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"


class FakeContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def read_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        return self.items[item]

    def upsert_item(self, body):
        self.items[body["id"]] = body
        return body

    def create_item(self, body):
        self.items[body["id"]] = body
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
        rows = list(self.get_container(container_name).items.values())
        param_map = {p["name"]: p["value"] for p in (params or [])}
        if "c.adventureId = @adventureId" in sql:
            rows = [r for r in rows if r.get("adventureId") == param_map.get("@adventureId")]
        if "c.status = 'active'" in sql:
            rows = [r for r in rows if r.get("status") == "active"]
        return rows


def _story(**overrides) -> Story:
    defaults = dict(
        id="story-1",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-08-30T00:00:00Z",
        contentUpdatedAt="2026-08-30T00:00:00Z",
    )
    defaults.update(overrides)
    return Story(**defaults)


def _session(adventure_id: str, player_id: str, status: str = "active") -> PlaySession:
    return PlaySession(
        id=str(uuid.uuid4()),
        adventureId=adventure_id,
        playerId=player_id,
        characterName="Wren",
        characterType="Curious Cousin",
        startedAt="2026-09-06T00:00:00Z",
        lastInteractionAt="2026-09-06T00:00:00Z",
        status=status,
        turns=[
            PlayerInteraction(
                turnNumber=0,
                narrativeText="Opening.",
                suggestedActions=["a", "b"],
                locationLabel="Entrance",
                timestamp="2026-09-06T00:00:00Z",
            )
        ],
    )


def _services_with(story: Story | None, sessions: list[PlaySession] | None = None):
    cosmos = FakeCosmosService()
    stories = StoryService(cosmos_service=cosmos)
    if story is not None:
        cosmos.get_container(config.STORIES_CONTAINER).upsert_item(story.to_dict())
    for session in sessions or []:
        cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).upsert_item(session.to_dict())
    play_sessions = PlaySessionService(cosmos_service=cosmos, story_service=stories)
    return stories, play_sessions, cosmos


def _authorized(request_factory, story_id):
    return request_factory(
        method="DELETE",
        url=f"/api/manage/stories/{story_id}",
        token="valid-token",
        route_params={"storyId": story_id},
    )


def _patched_authorize_admin():
    return patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None))


# --- Basic delete lifecycle (contracts/api.md, SC-001) ---


def test_delete_returns_200_and_removes_the_story(request_factory):
    story = _story()
    stories, play_sessions, _cosmos = _services_with(story)

    with _patched_authorize_admin():
        response = delete_story(
            _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
        )

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body == {"status": "deleted", "storyId": story.id}


def test_get_after_delete_returns_404(request_factory):
    story = _story()
    stories, play_sessions, _cosmos = _services_with(story)

    with _patched_authorize_admin():
        delete_story(_authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions)
        get_response = get_story(
            request_factory(
                method="GET",
                url=f"/api/manage/stories/{story.id}",
                token="valid-token",
                route_params={"storyId": story.id},
            ),
            story_service=stories,
        )

    assert get_response.status_code == 404


def test_delete_returns_404_for_a_story_id_that_never_existed(request_factory):
    stories, play_sessions, _cosmos = _services_with(None)

    with _patched_authorize_admin():
        response = delete_story(
            _authorized(request_factory, "missing"), story_service=stories, play_session_service=play_sessions
        )

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_deleting_an_already_deleted_story_returns_404_not_a_fresh_200(request_factory):
    story = _story()
    stories, play_sessions, _cosmos = _services_with(story)

    with _patched_authorize_admin():
        first = delete_story(
            _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
        )
        second = delete_story(
            _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
        )

    assert first.status_code == 200
    assert second.status_code == 404
    assert json.loads(second.get_body())["error"] == "not_found"


def test_delete_succeeds_for_a_published_story(request_factory):
    story = _story(published=True)
    stories, play_sessions, _cosmos = _services_with(story)

    with _patched_authorize_admin():
        response = delete_story(
            _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
        )

    assert response.status_code == 200


def test_delete_succeeds_for_an_unpublished_story(request_factory):
    story = _story(published=False)
    stories, play_sessions, _cosmos = _services_with(story)

    with _patched_authorize_admin():
        response = delete_story(
            _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
        )

    assert response.status_code == 200


def test_delete_rejects_unauthenticated_request(request_factory):
    story = _story()
    stories, play_sessions, _cosmos = _services_with(story)

    response = delete_story(
        _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
    )

    assert response.status_code in (401, 403)


# --- Delete cascade (FR-004, quickstart.md Scenario 4) ---


def test_delete_removes_a_single_active_session_for_the_story(request_factory):
    story = _story()
    session = _session(story.id, "player-1")
    stories, play_sessions, cosmos = _services_with(story, [session])

    with _patched_authorize_admin():
        delete_story(_authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions)

    assert session.id not in cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).items


def test_delete_removes_sessions_from_multiple_players(request_factory):
    story = _story()
    session_a = _session(story.id, "player-1")
    session_b = _session(story.id, "player-2")
    stories, play_sessions, cosmos = _services_with(story, [session_a, session_b])

    with _patched_authorize_admin():
        delete_story(_authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions)

    sessions_left = cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).items
    assert session_a.id not in sessions_left
    assert session_b.id not in sessions_left


def test_delete_leaves_a_concluded_session_for_that_story_in_place(request_factory):
    story = _story()
    concluded = _session(story.id, "player-1", status="concluded")
    stories, play_sessions, cosmos = _services_with(story, [concluded])

    with _patched_authorize_admin():
        delete_story(_authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions)

    assert concluded.id in cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).items


def test_delete_with_no_sessions_still_succeeds(request_factory):
    story = _story()
    stories, play_sessions, _cosmos = _services_with(story)

    with _patched_authorize_admin():
        response = delete_story(
            _authorized(request_factory, story.id), story_service=stories, play_session_service=play_sessions
        )

    assert response.status_code == 200
