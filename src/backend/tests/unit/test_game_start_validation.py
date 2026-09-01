"""Unit tests for POST /api/game/start's setup-validation logic (006-adventure-and-
character-setup FR-002, FR-003, FR-003a, FR-004a, contracts/api.md). Authorization is
bypassed via a patched authorize_player so these tests focus purely on field validation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.game.start import start
from backend.models.story import CharacterType

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def _story(story_id="story-1", published=True, character_types=None):
    story = MagicMock()
    story.id = story_id
    story.published = published
    story.characterTypes = character_types or [CharacterType(name="Detective"), CharacterType(name="Ghost")]
    return story


def _call(request_factory, body: dict, story=None):
    req = request_factory(method="POST", url="/api/game/start", token="valid-token", body=json.dumps(body).encode())
    story_service = MagicMock()
    story_service.get_story.return_value = story
    with patch("backend.api.game.start.authorize_player", return_value=(True, USER_OID, None)):
        return start(req, story_service=story_service)


def test_blank_character_name_rejected(request_factory):
    response = _call(request_factory, {"adventureId": "story-1", "characterName": "   ", "characterType": "Detective"}, _story())

    assert response.status_code == 400
    assert "characterName" in json.loads(response.get_body())["fields"]


def test_character_name_over_50_chars_rejected(request_factory):
    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "x" * 51, "characterType": "Detective"},
        _story(),
    )

    assert response.status_code == 400
    assert "characterName" in json.loads(response.get_body())["fields"]


def test_missing_character_type_rejected(request_factory):
    response = _call(request_factory, {"adventureId": "story-1", "characterName": "Wren"}, _story())

    assert response.status_code == 400
    assert "characterType" in json.loads(response.get_body())["fields"]


def test_character_type_from_a_different_adventure_rejected(request_factory):
    story = _story(character_types=[CharacterType(name="Detective")])
    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "Wren", "characterType": "Ghost"},
        story,
    )

    assert response.status_code == 400
    assert "characterType" in json.loads(response.get_body())["fields"]


def test_all_valid_fields_accepted(request_factory):
    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "Wren", "characterType": "Detective"},
        _story(),
    )

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body == {
        "status": "success",
        "adventureId": "story-1",
        "characterName": "Wren",
        "characterType": "Detective",
    }


def test_missing_adventure_id_rejected(request_factory):
    response = _call(request_factory, {"characterName": "Wren", "characterType": "Detective"})

    assert response.status_code == 400
    assert "adventureId" in json.loads(response.get_body())["fields"]


def test_unpublished_adventure_returns_404(request_factory):
    response = _call(
        request_factory,
        {"adventureId": "story-1", "characterName": "Wren", "characterType": "Detective"},
        _story(published=False),
    )

    assert response.status_code == 404


def test_nonexistent_adventure_returns_404(request_factory):
    response = _call(
        request_factory,
        {"adventureId": "missing", "characterName": "Wren", "characterType": "Detective"},
        None,
    )

    assert response.status_code == 404
