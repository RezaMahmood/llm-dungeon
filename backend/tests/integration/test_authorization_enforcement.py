"""Comprehensive authorization enforcement tests across endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.admin.stories import create_story
from backend.api.auth.me import me
from backend.api.game.start import start

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_me_403_for_non_allow_listed(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="t")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service)

    assert response.status_code == 403


def test_admin_403_without_administrator_capability(request_factory):
    req = request_factory(method="POST", url="/api/admin/stories/create", token="t")

    with patch("backend.api.admin.middleware.authenticate", return_value=(True, USER_OID, None)), patch(
        "backend.api.admin.middleware.AllowListService"
    ) as MockAllowList, patch("backend.api.admin.middleware.CapabilityService") as MockCapability:
        MockAllowList.return_value.get_allow_list_entry.return_value = MagicMock()
        MockCapability.return_value.get_user_capabilities.return_value = set()

        response = create_story(req)

    assert response.status_code == 403


def test_game_403_without_player_capability(request_factory):
    req = request_factory(method="POST", url="/api/game/start", token="t")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = MagicMock()
    capability_service = MagicMock()
    capability_service.get_user_capabilities.return_value = set()

    with patch("backend.api.game.start.authenticate", return_value=(True, USER_OID, None)):
        response = start(req, allow_list_service=allow_list_service, capability_service=capability_service)

    assert response.status_code == 403


def test_error_responses_never_expose_oid(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="t")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req, allow_list_service=allow_list_service)

    assert USER_OID not in response.get_body().decode()


def test_all_403_responses_use_identical_generic_body_for_allow_list_denial(request_factory):
    req1 = request_factory(method="GET", url="/api/auth/me", token="t")
    allow_list_service = MagicMock()
    allow_list_service.get_allow_list_entry.return_value = None

    with patch("backend.api.auth.me.authenticate", return_value=(True, USER_OID, None)):
        response = me(req1, allow_list_service=allow_list_service)

    assert json.loads(response.get_body()) == {"error": "access_denied", "message": "Access not granted"}
