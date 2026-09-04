"""Integration tests for GET /api/game/adventures and GET /api/game/adventures/{adventureId}
(006-adventure-and-character-setup, contracts/api.md, FR-001, FR-006, FR-007)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.game.adventures import get_adventure, list_adventures
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.story_service import StoryService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "player@example.com"


def _published_story(story_id="story-1"):
    return Story(
        id=story_id,
        name="Nine Doors of Mudlark Hall",
        worldPrompt="A crumbling manor of eight lying doors.",
        characterTypes=[CharacterType(name="Detective", description="Sharp-eyed."), CharacterType(name="Ghost")],
        completionCriteria=CompletionCriteria(successConditions=["Find the ninth door"]),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-08-30T00:00:00Z",
        contentUpdatedAt="2026-08-30T00:00:00Z",
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


def test_list_adventures_returns_only_published_summaries(request_factory):
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {"id": "story-1", "name": "Nine Doors of Mudlark Hall", "tone": "Mystery", "sessionLengthMinutes": 20, "readingLevel": "Year 5"}
    ]
    story_service = StoryService(cosmos_service=cosmos)
    req = request_factory(method="GET", url="/api/game/adventures", token="valid-token")

    with _patched_auth():
        response = list_adventures(req, story_service=story_service, account_provisioning_service=_authorized_player())

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["adventures"] == [
        {"id": "story-1", "name": "Nine Doors of Mudlark Hall", "tone": "Mystery", "sessionLengthMinutes": 20, "readingLevel": "Year 5"}
    ]
    assert "published" not in body["adventures"][0]


def test_list_adventures_returns_empty_array_when_none_published(request_factory):
    cosmos = MagicMock()
    cosmos.query.return_value = []
    story_service = StoryService(cosmos_service=cosmos)
    req = request_factory(method="GET", url="/api/game/adventures", token="valid-token")

    with _patched_auth():
        response = list_adventures(req, story_service=story_service, account_provisioning_service=_authorized_player())

    assert response.status_code == 200
    assert json.loads(response.get_body())["adventures"] == []


def test_list_adventures_denies_non_player(request_factory):
    entry = MagicMock()
    entry.roles = ["Administrator"]
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)
    req = request_factory(method="GET", url="/api/game/adventures", token="valid-token")

    with _patched_auth():
        response = list_adventures(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403


def test_list_adventures_requires_authentication(request_factory):
    req = request_factory(method="GET", url="/api/game/adventures")

    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(False, None, None, "no token")):
        response = list_adventures(req)

    assert response.status_code == 401


def test_get_adventure_returns_character_types_for_published_story(request_factory):
    cosmos = MagicMock()
    story_service = StoryService(cosmos_service=cosmos)
    story = _published_story()
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()
    req = request_factory(method="GET", url="/api/game/adventures/story-1", route_params={"adventureId": "story-1"}, token="valid-token")

    with _patched_auth():
        response = get_adventure(req, story_service=story_service, account_provisioning_service=_authorized_player())

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["adventure"]["characterTypes"] == [
        {"name": "Detective", "description": "Sharp-eyed."},
        {"name": "Ghost", "description": None},
    ]


def test_get_adventure_returns_404_for_unpublished_story(request_factory):
    cosmos = MagicMock()
    story_service = StoryService(cosmos_service=cosmos)
    story = _published_story()
    story.published = False
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()
    req = request_factory(method="GET", url="/api/game/adventures/story-1", route_params={"adventureId": "story-1"}, token="valid-token")

    with _patched_auth():
        response = get_adventure(req, story_service=story_service, account_provisioning_service=_authorized_player())

    assert response.status_code == 404


def test_get_adventure_returns_404_for_nonexistent_story(request_factory):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    story_service = StoryService(cosmos_service=cosmos)
    req = request_factory(method="GET", url="/api/game/adventures/missing", route_params={"adventureId": "missing"}, token="valid-token")

    with _patched_auth():
        response = get_adventure(req, story_service=story_service, account_provisioning_service=_authorized_player())

    assert response.status_code == 404
    assert json.loads(response.get_body()) == {"error": "not_found", "message": "Adventure not found"}
