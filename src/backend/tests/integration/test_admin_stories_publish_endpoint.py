"""Integration tests for POST /api/manage/stories/{storyId}/publish and .../unpublish
(contracts/api.md, FR-006, FR-007, FR-008, FR-011, FR-012). Cosmos is faked in-memory,
following the FakeCosmosService pattern in test_admin_stories_endpoint.py."""

from __future__ import annotations

import json
from unittest.mock import patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.admin.stories import publish_story, unpublish_story
from backend.models.story import CharacterType, CompletionCriteria, Story
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


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        return list(self.get_container(container_name).items.values())


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


def _service_with(story: Story | None) -> StoryService:
    from backend.config import config

    cosmos = FakeCosmosService()
    service = StoryService(cosmos_service=cosmos)
    if story is not None:
        cosmos.get_container(config.STORIES_CONTAINER).upsert_item(story.to_dict())
    return service


def _authorized(request_factory, story_id, action):
    return request_factory(
        method="POST",
        url=f"/api/manage/stories/{story_id}/{action}",
        token="valid-token",
        route_params={"storyId": story_id},
    )


def _patched_authorize_admin():
    return patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None))


# --- 404s ---


def test_publish_returns_404_for_nonexistent_story(request_factory):
    service = _service_with(None)
    with _patched_authorize_admin():
        response = publish_story(_authorized(request_factory, "missing", "publish"), story_service=service)

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_unpublish_returns_404_for_nonexistent_story(request_factory):
    service = _service_with(None)
    with _patched_authorize_admin():
        response = unpublish_story(_authorized(request_factory, "missing", "unpublish"), story_service=service)

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


# --- FR-008 gate ---


def test_publish_returns_409_test_play_required_when_gate_unsatisfied(request_factory):
    story = _story(lastTestPlayedAt=None)
    service = _service_with(story)

    with _patched_authorize_admin():
        response = publish_story(_authorized(request_factory, story.id, "publish"), story_service=service)

    assert response.status_code == 409
    body = json.loads(response.get_body())
    assert body["error"] == "test_play_required"
    assert "test-played" in body["message"]


def test_publish_succeeds_when_gate_satisfied(request_factory):
    story = _story(contentUpdatedAt="2026-08-30T09:00:00Z", lastTestPlayedAt="2026-08-30T09:00:00Z")
    service = _service_with(story)

    with _patched_authorize_admin():
        response = publish_story(_authorized(request_factory, story.id, "publish"), story_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert body["story"]["published"] is True
    assert body["story"]["lastPublishedAt"] is not None


# --- Idempotency (FR-006) ---


def test_redundant_publish_returns_200_idempotently(request_factory):
    story = _story(
        contentUpdatedAt="2026-08-30T09:00:00Z",
        lastTestPlayedAt="2026-08-30T09:00:00Z",
        published=True,
        lastPublishedAt="2026-08-30T09:05:00Z",
    )
    service = _service_with(story)

    with _patched_authorize_admin():
        response = publish_story(_authorized(request_factory, story.id, "publish"), story_service=service)

    assert response.status_code == 200
    assert json.loads(response.get_body())["story"]["published"] is True


def test_unpublish_returns_200_with_published_false_and_unchanged_last_published_at(request_factory):
    story = _story(published=True, lastPublishedAt="2026-08-30T09:05:00Z")
    service = _service_with(story)

    with _patched_authorize_admin():
        response = unpublish_story(_authorized(request_factory, story.id, "unpublish"), story_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["story"]["published"] is False
    assert body["story"]["lastPublishedAt"] == "2026-08-30T09:05:00Z"


def test_redundant_unpublish_returns_200_idempotently(request_factory):
    story = _story(published=False, lastPublishedAt="2026-08-30T09:05:00Z")
    service = _service_with(story)

    with _patched_authorize_admin():
        response = unpublish_story(_authorized(request_factory, story.id, "unpublish"), story_service=service)

    assert response.status_code == 200
    assert json.loads(response.get_body())["story"]["published"] is False


# --- Access control (Principle II) ---


def test_publish_rejects_unauthenticated_request(request_factory):
    story = _story(contentUpdatedAt="2026-08-30T09:00:00Z", lastTestPlayedAt="2026-08-30T09:00:00Z")
    service = _service_with(story)

    response = publish_story(_authorized(request_factory, story.id, "publish"), story_service=service)

    assert response.status_code in (401, 403)


def test_unpublish_rejects_unauthenticated_request(request_factory):
    story = _story(published=True)
    service = _service_with(story)

    response = unpublish_story(_authorized(request_factory, story.id, "unpublish"), story_service=service)

    assert response.status_code in (401, 403)
