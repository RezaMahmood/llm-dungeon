"""Integration tests for a user holding both Player and Administrator capabilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.me import me
from backend.models.allow_list_entry import AllowListEntry

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_me_for_dual_role_user_returns_both_capabilities(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    entry = AllowListEntry(user_oid=USER_OID, email="dual@example.com", dateAdded="2026-08-28T20:00:00Z")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = entry
    capability_service = MagicMock()
    capability_service.get_user_capabilities.return_value = {"Player", "Administrator"}

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 200
    body = response.get_body().decode()
    assert '"hasPlayer": true' in body or '"hasPlayer":true' in body
    assert '"hasAdministrator": true' in body or '"hasAdministrator":true' in body
