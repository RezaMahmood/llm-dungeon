"""Integration tests for POST /api/auth/login."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.login import login
from backend.models.allow_list_entry import AllowListEntry

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def _mock_services(entry=None, capabilities=None):
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = entry
    capability_service = MagicMock()
    capability_service.get_user_capabilities.return_value = capabilities or set()
    return allow_list_service, capability_service


def test_login_valid_token_allow_listed_player_returns_200(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    entry = AllowListEntry(user_oid=USER_OID, email="player@example.com", dateAdded="2026-08-28T20:00:00Z")
    allow_list_service, capability_service = _mock_services(entry=entry, capabilities={"Player"})

    with patch("backend.api.auth.login.authenticate", return_value=(True, USER_OID, None)):
        response = login(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 200
    body = response.get_body().decode()
    assert '"hasPlayer": true' in body or '"hasPlayer":true' in body
    assert '"hasAdministrator": false' in body or '"hasAdministrator":false' in body


def test_login_valid_token_not_allow_listed_returns_403(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    allow_list_service, capability_service = _mock_services(entry=None)

    with patch("backend.api.auth.login.authenticate", return_value=(True, USER_OID, None)):
        response = login(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 403


def test_login_expired_token_returns_401(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="expired-token")

    with patch("backend.api.auth.login.authenticate", return_value=(False, None, "Invalid or expired token")):
        response = login(req)

    assert response.status_code == 401
