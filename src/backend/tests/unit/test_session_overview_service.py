"""Unit tests for SessionOverviewService (026-token-usage data-model.md → Read model:
Session Overview Row; research.md Decision 7)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.services.play_session_service import SessionNotFoundError as PlaySessionNotFoundError
from backend.services.session_overview_service import (
    DELETED_STORY_LABEL,
    UNPROVISIONED_ACCOUNT_LABEL,
    SessionNotFoundError,
    SessionOverviewService,
)
from backend.services import test_play_session_service as test_play_module

PLAYER_OID = "oid-player-1"
ADMIN_OID = "oid-admin-1"


def _service(player_rows=None, test_rows=None, story_names=None, accounts=None):
    cosmos = MagicMock()

    def query(container_name, sql, params=None, partition_key=None):  # noqa: ARG001
        if "'PlaySession'" in sql:
            return player_rows or []
        return test_rows or []

    cosmos.query.side_effect = query

    stories = MagicMock()
    story_names = story_names or {}
    stories.get_story_name.side_effect = lambda story_id: story_names.get(story_id)

    accounts_service = MagicMock()
    accounts_service.list_all.return_value = accounts or []

    return SessionOverviewService(
        cosmos_service=cosmos, story_service=stories, account_provisioning_service=accounts_service
    )


def test_list_sessions_combines_player_and_test_sessions():
    service = _service(
        player_rows=[{"id": "session-p1", "adventureId": "story-1", "playerId": PLAYER_OID, "totalTokens": 6420}],
        test_rows=[{"id": "session-t1", "storyId": "story-1", "administratorId": ADMIN_OID, "totalTokens": 1180}],
        story_names={"story-1": "The Salt Mines"},
        accounts=[
            ProvisionedAccountEntry(email="player@example.com", roles=["Player"], objectId=PLAYER_OID),
            ProvisionedAccountEntry(email="admin@example.com", roles=["Administrator"], objectId=ADMIN_OID),
        ],
    )

    sessions = service.list_sessions()

    assert sessions == [
        {
            "sessionId": "session-p1",
            "sessionType": "player",
            "storyId": "story-1",
            "storyName": "The Salt Mines",
            "totalTokens": 6420,
            "email": "player@example.com",
        },
        {
            "sessionId": "session-t1",
            "sessionType": "test",
            "storyId": "story-1",
            "storyName": "The Salt Mines",
            "totalTokens": 1180,
            "email": "admin@example.com",
        },
    ]


def test_list_sessions_falls_back_for_a_deleted_story():
    service = _service(
        player_rows=[{"id": "session-p1", "adventureId": "missing-story", "playerId": PLAYER_OID, "totalTokens": 10}],
        story_names={},
        accounts=[ProvisionedAccountEntry(email="player@example.com", roles=["Player"], objectId=PLAYER_OID)],
    )

    [row] = service.list_sessions()

    assert row["storyName"] == DELETED_STORY_LABEL


def test_list_sessions_falls_back_for_an_unprovisioned_account():
    service = _service(
        player_rows=[{"id": "session-p1", "adventureId": "story-1", "playerId": "no-longer-provisioned", "totalTokens": 10}],
        story_names={"story-1": "The Salt Mines"},
        accounts=[],
    )

    [row] = service.list_sessions()

    assert row["email"] == UNPROVISIONED_ACCOUNT_LABEL


def test_list_sessions_renders_zero_tokens_for_a_turnless_session():
    service = _service(
        player_rows=[{"id": "session-p1", "adventureId": "story-1", "playerId": PLAYER_OID, "totalTokens": 0}],
        story_names={"story-1": "The Salt Mines"},
        accounts=[ProvisionedAccountEntry(email="player@example.com", roles=["Player"], objectId=PLAYER_OID)],
    )

    [row] = service.list_sessions()

    assert row["totalTokens"] == 0


def test_list_sessions_resolves_each_distinct_story_name_only_once():
    service = _service(
        player_rows=[
            {"id": "session-p1", "adventureId": "story-1", "playerId": PLAYER_OID, "totalTokens": 10},
            {"id": "session-p2", "adventureId": "story-1", "playerId": PLAYER_OID, "totalTokens": 20},
        ],
        story_names={"story-1": "The Salt Mines"},
        accounts=[ProvisionedAccountEntry(email="player@example.com", roles=["Player"], objectId=PLAYER_OID)],
    )

    service.list_sessions()

    service._stories.get_story_name.assert_called_once_with("story-1")


def test_list_sessions_returns_empty_list_when_nothing_exists():
    service = _service()

    assert service.list_sessions() == []


def test_list_sessions_queries_regardless_of_status(monkeypatch):
    """data-model.md → Session Overview Row: 'every session appears exactly once,
    regardless of status (active/concluded)' — spot-checked here since neither query
    string filters on it (026-token-usage tasks.md T050)."""
    cosmos = MagicMock()
    queries = []

    def query(container_name, sql, params=None, partition_key=None):  # noqa: ARG001
        queries.append(sql)
        return []

    cosmos.query.side_effect = query
    service = SessionOverviewService(
        cosmos_service=cosmos,
        story_service=MagicMock(),
        account_provisioning_service=MagicMock(list_all=MagicMock(return_value=[])),
    )

    service.list_sessions()

    assert len(queries) == 2
    assert all("status" not in sql for sql in queries)


# --- Deleting a session (031-sessions-admin-design-spec FR-006, research.md Decision 1) ---


def _delete_service(play_service=None, test_play_service=None):
    return SessionOverviewService(
        cosmos_service=MagicMock(),
        story_service=MagicMock(),
        account_provisioning_service=MagicMock(),
        play_session_service=play_service or MagicMock(),
        test_play_session_service=test_play_service or MagicMock(),
    )


def test_delete_session_deletes_a_player_session_without_touching_test_play():
    play = MagicMock()
    test_play = MagicMock()
    service = _delete_service(play, test_play)

    assert service.delete_session("session-p1") == "player"

    play.delete_session_as_administrator.assert_called_once_with("session-p1")
    # The id resolved in the first container, so the second is never reached.
    test_play.delete_session_as_administrator.assert_not_called()


def test_delete_session_falls_back_to_the_test_play_container():
    play = MagicMock()
    play.delete_session_as_administrator.side_effect = PlaySessionNotFoundError()
    test_play = MagicMock()
    service = _delete_service(play, test_play)

    assert service.delete_session("session-t1") == "test"

    test_play.delete_session_as_administrator.assert_called_once_with("session-t1")


def test_delete_session_raises_when_neither_container_holds_the_id():
    play = MagicMock()
    play.delete_session_as_administrator.side_effect = PlaySessionNotFoundError()
    test_play = MagicMock()
    test_play.delete_session_as_administrator.side_effect = test_play_module.SessionNotFoundError()
    service = _delete_service(play, test_play)

    with pytest.raises(SessionNotFoundError):
        service.delete_session("nope")
