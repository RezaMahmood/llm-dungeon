"""Unit tests for SessionOverviewService (026-token-usage data-model.md → Read model:
Session Overview Row; research.md Decision 7)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.services.session_overview_service import (
    DELETED_STORY_LABEL,
    UNPROVISIONED_ACCOUNT_LABEL,
    SessionOverviewService,
)

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
