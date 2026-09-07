"""Integration tests for GET /api/game/sessions, GET .../{sessionId}, and
POST .../{sessionId}/checkpoints (009-save-and-continue, contracts/api.md). Cosmos is
faked in-memory, matching this repo's other integration tests."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.api.game.sessions import create_checkpoint, get_session, list_sessions
from backend.config import config
from backend.models.play_session import PlayerInteraction, PlaySession
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.services.play_session_service import PlaySessionService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_OID = "660e8400-e29b-41d4-a716-446655440111"


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


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        rows = list(self.get_container(container_name).items.values())
        param_map = {p["name"]: p["value"] for p in (params or [])}
        if "c.playerId = @playerId" in sql:
            rows = [r for r in rows if r.get("playerId") == param_map.get("@playerId")]
        if "c.status = 'active'" in sql:
            rows = [r for r in rows if r.get("status") == "active"]
        if "ARRAY_SLICE(c.turns, -1) AS latestTurn" in sql:
            rows = [_project_saved_game_summary_row(r) for r in rows]
        return rows


def _project_saved_game_summary_row(row: dict) -> dict:
    """Simulates the real Cosmos SQL projection `list_player_sessions` issues
    (`ARRAY_SLICE(c.turns, -1)`, `ARRAY_LENGTH(...)`), so tests exercise the same
    lean-row shape production actually receives rather than a full document."""
    turns = row.get("turns", [])
    return {
        "id": row["id"],
        "adventureId": row["adventureId"],
        "characterName": row["characterName"],
        "startedAt": row["startedAt"],
        "lastInteractionAt": row["lastInteractionAt"],
        "isActiveForPlayer": row["isActiveForPlayer"],
        "latestTurn": turns[-1:],
        "turnCount": len(turns),
        "checkpointCount": len(row.get("checkpoints", [])),
    }


def _story(**overrides) -> Story:
    return Story(
        id=str(uuid.uuid4()),
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A half-abandoned lighthouse on a foggy cove.",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"], failureConditions=[]),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-09-05T00:00:00Z",
        contentUpdatedAt="2026-09-05T00:00:00Z",
        published=True,
        **overrides,
    )


def _existing_session(cosmos: FakeCosmosService, story: Story, player_id: str = USER_OID, **overrides) -> PlaySession:
    now = "2026-09-05T00:00:00Z"
    session = PlaySession(
        id=str(uuid.uuid4()),
        adventureId=story.id,
        playerId=player_id,
        characterName="Wren",
        characterType="Curious Cousin",
        startedAt=now,
        lastInteractionAt=now,
        turns=[
            PlayerInteraction(
                turnNumber=0,
                narrativeText="The lighthouse door creaks open.",
                suggestedActions=["look around"],
                locationLabel="Lighthouse entrance",
                timestamp=now,
            )
        ],
    )
    for key, value in overrides.items():
        setattr(session, key, value)
    cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).upsert_item(session.to_dict())
    return session


def _service(story: Story, cosmos: FakeCosmosService | None = None) -> tuple[PlaySessionService, FakeCosmosService]:
    cosmos = cosmos or FakeCosmosService()
    cosmos.get_container(config.STORIES_CONTAINER).upsert_item(story.to_dict())
    service = PlaySessionService(cosmos_service=cosmos, llm_service=MagicMock())
    return service, cosmos


def _authorized_player():
    entry = MagicMock()
    entry.roles = ["Player"]
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)
    return account_provisioning_service


def _patched_auth(oid: str = USER_OID):
    return patch("backend.api.game.middleware.authenticate_with_email", return_value=(True, oid, "player@example.com", None))


def _list(request_factory, service, oid=USER_OID):
    req = request_factory(method="GET", url="/api/game/sessions", token="valid-token")
    with _patched_auth(oid):
        return list_sessions(req, play_session_service=service, account_provisioning_service=_authorized_player())


def _get(request_factory, service, session_id, oid=USER_OID):
    req = request_factory(
        method="GET", url=f"/api/game/sessions/{session_id}", token="valid-token", route_params={"sessionId": session_id}
    )
    with _patched_auth(oid):
        return get_session(req, play_session_service=service, account_provisioning_service=_authorized_player())


def _checkpoint(request_factory, service, session_id, oid=USER_OID):
    req = request_factory(
        method="POST",
        url=f"/api/game/sessions/{session_id}/checkpoints",
        token="valid-token",
        route_params={"sessionId": session_id},
    )
    with _patched_auth(oid):
        return create_checkpoint(req, play_session_service=service, account_provisioning_service=_authorized_player())


def test_unauthenticated_list_rejected(request_factory):
    story = _story()
    service, _cosmos = _service(story)
    req = request_factory(method="GET", url="/api/game/sessions")
    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(False, None, None, "No token")):
        response = list_sessions(req, play_session_service=service, account_provisioning_service=_authorized_player())
    assert response.status_code in (401, 403)


# --- GET /api/game/sessions ---


def test_list_sessions_returns_200_with_callers_rows(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)

    response = _list(request_factory, service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert [row["sessionId"] for row in body["sessions"]] == [session.id]
    assert "turns" not in body["sessions"][0]


def test_list_sessions_returns_200_with_empty_list_for_player_with_none(request_factory):
    story = _story()
    service, _cosmos = _service(story)

    response = _list(request_factory, service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["sessions"] == []


def test_list_sessions_excludes_another_players_sessions(request_factory):
    story = _story()
    service, cosmos = _service(story)
    _existing_session(cosmos, story, player_id=OTHER_OID)

    response = _list(request_factory, service)

    assert json.loads(response.get_body())["sessions"] == []


def test_list_sessions_excludes_concluded_sessions(request_factory):
    story = _story()
    service, cosmos = _service(story)
    _existing_session(cosmos, story, status="concluded", completionReason={"type": "success", "detail": "x"})

    response = _list(request_factory, service)

    assert json.loads(response.get_body())["sessions"] == []


# --- GET /api/game/sessions/{sessionId} ---


def test_get_session_returns_200_with_every_turn_and_full_summary_for_owner(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)

    response = _get(request_factory, service, session.id)

    assert response.status_code == 200
    body = json.loads(response.get_body())["session"]
    assert body["sessionId"] == session.id
    assert body["adventureName"] == story.name
    assert body["characterType"] == "Curious Cousin"
    assert body["status"] == "active"
    assert len(body["turns"]) == 1
    assert body["checkpoints"] == []


def test_get_session_returns_403_for_another_player_never_404(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)

    response = _get(request_factory, service, session.id, oid=OTHER_OID)

    assert response.status_code == 403
    body = json.loads(response.get_body())
    assert body["error"] == "access_denied"


def test_get_session_returns_404_for_unknown_id(request_factory):
    story = _story()
    service, _cosmos = _service(story)

    response = _get(request_factory, service, "no-such-session")

    assert response.status_code == 404


# --- POST /api/game/sessions/{sessionId}/checkpoints ---


def test_create_checkpoint_returns_201_with_marker_body(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)

    response = _checkpoint(request_factory, service, session.id)

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert body["checkpoint"]["label"] == "Lighthouse entrance"
    assert body["checkpoint"]["turnNumber"] == 0
    assert body["checkpoint"]["createdAt"]


def test_create_checkpoint_returns_403_for_another_player(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)

    response = _checkpoint(request_factory, service, session.id, oid=OTHER_OID)

    assert response.status_code == 403


def test_create_checkpoint_returns_404_for_unknown_id(request_factory):
    story = _story()
    service, _cosmos = _service(story)

    response = _checkpoint(request_factory, service, "no-such-session")

    assert response.status_code == 404


def test_create_checkpoint_returns_409_session_concluded_for_finished_game(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story, status="concluded", completionReason={"type": "success", "detail": "x"})

    response = _checkpoint(request_factory, service, session.id)

    assert response.status_code == 409
    assert json.loads(response.get_body())["error"] == "session_concluded"


def test_create_checkpoint_returns_503_when_write_cannot_land(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)
    container = cosmos.get_container(config.PLAY_SESSIONS_CONTAINER)

    def always_conflicts(item, body, etag=None, match_condition=None):
        raise CosmosAccessConditionFailedError

    container.replace_item = always_conflicts

    response = _checkpoint(request_factory, service, session.id)

    assert response.status_code == 503
    assert json.loads(response.get_body())["error"] == "checkpoint_unavailable"


# --- Resume never rewinds (T025, FR-003a, FR-007) ---


def test_resuming_never_rewinds_a_checkpointed_session(request_factory):
    """Record a checkpoint, submit two further interactions directly against the
    service, then confirm the detail read shows every post-checkpoint turn and the
    marker still reports its original turnNumber — nothing discarded or rewound."""
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)

    checkpoint_response = _checkpoint(request_factory, service, session.id)
    assert checkpoint_response.status_code == 201
    checkpointed_turn_number = json.loads(checkpoint_response.get_body())["checkpoint"]["turnNumber"]

    stored = PlaySession.from_dict(cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).items[session.id])
    for i in range(1, 3):
        stored.turns.append(
            PlayerInteraction(
                turnNumber=i,
                narrativeText=f"Turn {i}.",
                suggestedActions=["go"],
                locationLabel=f"Location {i}",
                timestamp="2026-09-05T00:0{}:00Z".format(i),
            )
        )
    stored.lastInteractionAt = "2026-09-05T00:10:00Z"
    cosmos.get_container(config.PLAY_SESSIONS_CONTAINER).upsert_item(stored.to_dict())

    response = _get(request_factory, service, session.id)

    assert response.status_code == 200
    body = json.loads(response.get_body())["session"]
    turn_numbers = [t["turnNumber"] for t in body["turns"]]
    assert turn_numbers == [0, 1, 2]
    assert body["checkpoints"][0]["turnNumber"] == checkpointed_turn_number


# --- Story deleted / unpublished (025-story-delete FR-007, FR-008, T016) ---


def test_get_session_against_deleted_story_returns_404_story_deleted(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)
    del cosmos.get_container(config.STORIES_CONTAINER).items[story.id]

    response = _get(request_factory, service, session.id)

    assert response.status_code == 404
    body = json.loads(response.get_body())
    assert body["error"] == "story_deleted"
    assert body["promptReturnToList"] is True


def test_get_session_against_unpublished_story_returns_409_story_unpublished(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story)
    cosmos.get_container(config.STORIES_CONTAINER).items[story.id]["published"] = False

    response = _get(request_factory, service, session.id)

    assert response.status_code == 409
    body = json.loads(response.get_body())
    assert body["error"] == "story_unpublished"
    assert body["promptReturnToList"] is True


def test_get_session_against_unpublished_story_still_succeeds_for_a_concluded_session(request_factory):
    story = _story()
    service, cosmos = _service(story)
    session = _existing_session(cosmos, story, status="concluded", completionReason={"type": "success", "detail": "x"})
    cosmos.get_container(config.STORIES_CONTAINER).items[story.id]["published"] = False

    response = _get(request_factory, service, session.id)

    assert response.status_code == 200


# --- list_sessions `available` field (025-story-delete FR-009, FR-011) ---


def test_list_sessions_marks_row_unavailable_when_story_unpublished(request_factory):
    story = _story()
    service, cosmos = _service(story)
    _existing_session(cosmos, story)
    cosmos.get_container(config.STORIES_CONTAINER).items[story.id]["published"] = False

    response = _list(request_factory, service)

    assert json.loads(response.get_body())["sessions"][0]["available"] is False


def test_list_sessions_marks_row_available_when_story_published(request_factory):
    story = _story()
    service, cosmos = _service(story)
    _existing_session(cosmos, story)

    response = _list(request_factory, service)

    assert json.loads(response.get_body())["sessions"][0]["available"] is True
