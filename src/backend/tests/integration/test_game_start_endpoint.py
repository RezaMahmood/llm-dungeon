"""Integration tests for POST /api/game/start (006-adventure-and-character-setup,
contracts/api.md, FR-002 through FR-005, FR-007). Cosmos is faked in-memory, matching this
repo's other integration tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.game.start import start
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.story_service import StoryService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "player@example.com"


class FakeContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def read_item(self, item, partition_key):  # noqa: ARG002
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

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


def _story_service_with(story: Story) -> StoryService:
    from backend.config import config

    cosmos = FakeCosmosService()
    service = StoryService(cosmos_service=cosmos)
    cosmos.get_container(config.STORIES_CONTAINER).upsert_item(story.to_dict())
    return service


def _published_story(story_id="story-1", character_types=None):
    return Story(
        id=story_id,
        name="Nine Doors of Mudlark Hall",
        worldPrompt="A crumbling manor of eight lying doors.",
        characterTypes=character_types or [CharacterType(name="Detective"), CharacterType(name="Ghost")],
        completionCriteria=CompletionCriteria(successConditions=["Find the ninth door"]),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-08-30T00:00:00Z",
        published=True,
    )


def _authorized_player():
    entry = MagicMock()
    entry.roles = ["Player"]
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)
    return account_provisioning_service


def _patched_auth():
    return patch("backend.api.game.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None))


def _call(request_factory, body, story_service):
    req = request_factory(method="POST", url="/api/game/start", token="valid-token", body=json.dumps(body).encode())
    with _patched_auth():
        return start(req, story_service=story_service, account_provisioning_service=_authorized_player())


def test_complete_valid_setup_returns_200_with_echoed_fields(request_factory):
    story_service = _story_service_with(_published_story())

    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "Wren", "characterType": "Detective"},
        story_service,
    )

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {
        "status": "success",
        "adventureId": "story-1",
        "characterName": "Wren",
        "characterType": "Detective",
    }


def test_missing_character_type_returns_400_with_field_identified(request_factory):
    story_service = _story_service_with(_published_story())

    response = _call(request_factory, {"adventureId": "story-1", "characterName": "Wren"}, story_service)

    assert response.status_code == 400
    assert "characterType" in json.loads(response.get_body())["fields"]


def test_character_type_from_a_different_adventure_returns_400(request_factory):
    story_service = _story_service_with(_published_story(character_types=[CharacterType(name="Detective")]))

    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "Wren", "characterType": "Ghost"},
        story_service,
    )

    assert response.status_code == 400
    assert "characterType" in json.loads(response.get_body())["fields"]


def test_unpublished_adventure_id_returns_404(request_factory):
    unpublished = _published_story()
    unpublished.published = False
    story_service = _story_service_with(unpublished)

    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "Wren", "characterType": "Detective"},
        story_service,
    )

    assert response.status_code == 404


def test_nonexistent_adventure_id_returns_404(request_factory):
    story_service = StoryService(cosmos_service=FakeCosmosService())

    response = _call(
        request_factory,
        {"adventureId": "missing", "characterName": "Wren", "characterType": "Detective"},
        story_service,
    )

    assert response.status_code == 404


def test_non_player_caller_is_denied(request_factory):
    story_service = _story_service_with(_published_story())
    entry = MagicMock()
    entry.roles = ["Administrator"]
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)
    req = request_factory(
        method="POST",
        url="/api/game/start",
        token="valid-token",
        body=json.dumps({"adventureId": "story-1", "characterName": "Wren", "characterType": "Detective"}).encode(),
    )

    with _patched_auth():
        response = start(req, story_service=story_service, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403
