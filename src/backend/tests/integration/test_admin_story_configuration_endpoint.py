"""Integration tests for GET /api/manage/stories/{storyId}/configuration (contracts/api.md;
quickstart.md scenario 3)."""

from __future__ import annotations

import json
from unittest.mock import patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.admin.stories import get_story_configuration
from backend.api.utils import forbidden_insufficient_permission, unauthorized
from backend.services import story_config_file
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


def _authorized(request_factory, story_id):
    return request_factory(
        method="GET",
        url=f"/api/manage/stories/{story_id}/configuration",
        token="valid-token",
        route_params={"storyId": story_id},
    )


def _patched_authorize_admin():
    return patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None))


def test_get_configuration_returns_serialized_bytes_with_content_type(request_factory, _story):
    cosmos = FakeCosmosService()
    story_service = StoryService(cosmos_service=cosmos)
    story = _story(id="story-1", name="The Sunken Library")
    cosmos.get_container("stories").upsert_item(story.to_dict())

    with _patched_authorize_admin():
        response = get_story_configuration(_authorized(request_factory, "story-1"), story_service=story_service)

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_body().decode("utf-8") == story_config_file.serialize(story)


def test_get_configuration_returns_404_for_missing_story(request_factory):
    story_service = StoryService(cosmos_service=FakeCosmosService())

    with _patched_authorize_admin():
        response = get_story_configuration(_authorized(request_factory, "missing"), story_service=story_service)

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_get_configuration_requires_authentication(request_factory):
    story_service = StoryService(cosmos_service=FakeCosmosService())
    with patch("backend.api.admin.stories.authorize_admin", return_value=(False, None, unauthorized())):
        response = get_story_configuration(_authorized(request_factory, "story-1"), story_service=story_service)
    assert response.status_code == 401


def test_get_configuration_requires_administrator_role(request_factory):
    story_service = StoryService(cosmos_service=FakeCosmosService())
    with patch(
        "backend.api.admin.stories.authorize_admin",
        return_value=(False, ADMIN_OID, forbidden_insufficient_permission()),
    ):
        response = get_story_configuration(_authorized(request_factory, "story-1"), story_service=story_service)
    assert response.status_code == 403
