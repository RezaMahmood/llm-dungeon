"""Integration tests for GET /api/auth/me."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.me import me
from backend.models.allow_list_entry import AllowListEntry

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_me_valid_player_token_returns_200_with_capabilities(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    entry = AllowListEntry(user_oid=USER_OID, email="player@example.com", dateAdded="2026-08-28T20:00:00Z")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = entry
    capability_service = MagicMock()
    capability_service.get_user_capabilities.return_value = {"Player"}

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 200
    assert USER_OID in response.get_body().decode()


def test_me_expired_token_returns_401(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="expired-token")

    with patch("backend.api.auth.me.authenticate", return_value=(False, None, "Invalid or expired token")):
        response = me(req)

    assert response.status_code == 401


def test_me_not_allow_listed_returns_403(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service)

    assert response.status_code == 403
