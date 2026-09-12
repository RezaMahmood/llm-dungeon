"""Integration tests for GET /api/manage/sessions (026-token-usage contracts/api.md)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.admin.sessions import list_sessions

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
