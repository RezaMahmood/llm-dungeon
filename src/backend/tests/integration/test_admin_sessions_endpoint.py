"""Integration tests for GET /api/manage/sessions (026-token-usage contracts/api.md) and
DELETE /api/manage/sessions/{sessionId} (031-sessions-admin-design-spec contracts/api.md)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.admin.sessions import delete_session, list_sessions
from backend.services.session_overview_service import SessionNotFoundError

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_list_sessions_returns_every_session_row(request_factory):
    req = request_factory(method="GET", url="/api/manage/sessions", token="valid-token")
    service = MagicMock()
    service.list_sessions.return_value = [
        {
            "sessionId": "b7e1",
            "sessionType": "player",
            "storyId": "9f2a",
            "storyName": "The Salt Mines",
            "totalTokens": 6420,
            "email": "player@example.com",
        },
        {
            "sessionId": "c3d9",
            "sessionType": "test",
            "storyId": "9f2a",
            "storyName": "The Salt Mines",
            "totalTokens": 1180,
            "email": "admin@example.com",
        },
    ]

    with patch("backend.api.admin.sessions.authorize_admin", return_value=(True, ADMIN_OID, None)):
        response = list_sessions(req, session_overview_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert len(body["sessions"]) == 2
    assert body["sessions"][0]["sessionType"] == "player"
    assert body["sessions"][1]["sessionType"] == "test"


def test_list_sessions_returns_empty_list_as_200_not_404(request_factory):
    req = request_factory(method="GET", url="/api/manage/sessions", token="valid-token")
    service = MagicMock()
    service.list_sessions.return_value = []

    with patch("backend.api.admin.sessions.authorize_admin", return_value=(True, ADMIN_OID, None)):
        response = list_sessions(req, session_overview_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["sessions"] == []


def test_list_sessions_returns_401_when_unauthenticated(request_factory):
    req = request_factory(method="GET", url="/api/manage/sessions")
    service = MagicMock()

    with patch(
        "backend.api.admin.sessions.authorize_admin", return_value=(False, None, MagicMock(status_code=401))
    ):
        response = list_sessions(req, session_overview_service=service)

    assert response.status_code == 401
    service.list_sessions.assert_not_called()


def test_list_sessions_returns_403_for_non_administrator(request_factory):
    req = request_factory(method="GET", url="/api/manage/sessions", token="valid-token")
    service = MagicMock()

    with patch(
        "backend.api.admin.sessions.authorize_admin", return_value=(False, ADMIN_OID, MagicMock(status_code=403))
    ):
        response = list_sessions(req, session_overview_service=service)

    assert response.status_code == 403
    service.list_sessions.assert_not_called()

# --- DELETE /api/manage/sessions/{sessionId} (031 FR-006/FR-010/FR-015) ---

SESSION_ID = "d668d9f8-9e26-4161-a95c-8500e8333219"


def _delete_request(request_factory, token="valid-token"):
    return request_factory(
        method="DELETE",
        url=f"/api/manage/sessions/{SESSION_ID}",
        token=token,
        route_params={"sessionId": SESSION_ID},
    )


def test_delete_session_removes_the_session(request_factory):
    req = _delete_request(request_factory)
    service = MagicMock()
    service.delete_session.return_value = "player"

    with patch("backend.api.admin.sessions.authorize_admin", return_value=(True, ADMIN_OID, None)):
        response = delete_session(req, session_overview_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body == {"status": "deleted", "sessionId": SESSION_ID}
    service.delete_session.assert_called_once_with(SESSION_ID)


def test_delete_session_removes_an_admin_test_play_session_the_same_way(request_factory):
    """FR-006: both kinds, resolved server-side from the id — the client never says which
    (research.md Decision 1)."""
    req = _delete_request(request_factory)
    service = MagicMock()
    service.delete_session.return_value = "test"

    with patch("backend.api.admin.sessions.authorize_admin", return_value=(True, ADMIN_OID, None)):
        response = delete_session(req, session_overview_service=service)

    assert response.status_code == 200
    service.delete_session.assert_called_once_with(SESSION_ID)


def test_delete_session_returns_404_when_already_deleted(request_factory):
    """The concurrent-delete case (FR-015): a second administrator deleting the same row."""
    req = _delete_request(request_factory)
    service = MagicMock()
    service.delete_session.side_effect = SessionNotFoundError()

    with patch("backend.api.admin.sessions.authorize_admin", return_value=(True, ADMIN_OID, None)):
        response = delete_session(req, session_overview_service=service)

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_delete_session_returns_401_when_unauthenticated(request_factory):
    req = _delete_request(request_factory, token=None)
    service = MagicMock()

    with patch(
        "backend.api.admin.sessions.authorize_admin", return_value=(False, None, MagicMock(status_code=401))
    ):
        response = delete_session(req, session_overview_service=service)

    assert response.status_code == 401
    service.delete_session.assert_not_called()


def test_delete_session_returns_403_for_non_administrator(request_factory):
    """FR-010: the destructive path is gated server-side, whatever the client offered."""
    req = _delete_request(request_factory)
    service = MagicMock()

    with patch(
        "backend.api.admin.sessions.authorize_admin", return_value=(False, ADMIN_OID, MagicMock(status_code=403))
    ):
        response = delete_session(req, session_overview_service=service)

    assert response.status_code == 403
    service.delete_session.assert_not_called()
