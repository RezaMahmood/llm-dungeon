"""Integration tests for denial scenarios (User Story 3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.admin.stories import create_story
from backend.api.auth.me import me
from backend.api.game.start import start

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_me_returns_403_for_non_allow_listed_user(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service)

    assert response.status_code == 403
    assert USER_OID not in response.get_body().decode()


def test_admin_endpoint_returns_403_without_administrator_capability(request_factory):
    req = request_factory(method="POST", url="/api/admin/stories/create", token="valid-token")

    with patch("backend.api.admin.middleware.authenticate", return_value=(True, USER_OID, None)), patch(
        "backend.api.admin.middleware.AllowListService"
    ) as MockAllowList, patch("backend.api.admin.middleware.CapabilityService") as MockCapability:
        MockAllowList.return_value.get_allow_list_entry.return_value = MagicMock()
        MockCapability.return_value.get_user_capabilities.return_value = {"Player"}

        response = create_story(req)

    assert response.status_code == 403


def test_game_endpoint_returns_403_without_player_capability(request_factory):
    req = request_factory(method="POST", url="/api/game/start", token="valid-token")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = MagicMock()
    capability_service = MagicMock()
    capability_service.get_user_capabilities.return_value = {"Administrator"}

    with patch("backend.api.game.start.authenticate", return_value=(True, USER_OID, None)):
        response = start(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 403


def test_all_denial_messages_are_generic_and_identical(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service)

    import json

    body = json.loads(response.get_body().decode())
    assert body == {"error": "access_denied", "message": "Access not granted"}
