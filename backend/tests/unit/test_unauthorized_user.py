"""Unit tests for denial of non-allow-listed users (User Story 3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.login import login
from backend.services.allow_list_service import AllowListService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_allow_list_service_returns_false_for_user_not_on_allow_list():
    cosmos = MagicMock()
    cosmos.query.return_value = []
    service = AllowListService(cosmos_service=cosmos)

    assert service.is_allowed(USER_OID) is False


def test_login_endpoint_returns_403_for_non_allow_listed_user(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")

    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None
    capability_service = MagicMock()

    with patch("backend.api.auth.login.authenticate", return_value=(True, USER_OID, None)):
        response = login(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 403
    body = response.get_body().decode()
    assert "Access not granted" in body
    assert USER_OID not in body
