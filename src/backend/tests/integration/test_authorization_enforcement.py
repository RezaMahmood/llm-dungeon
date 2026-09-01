"""Comprehensive authorization enforcement tests across endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.admin.stories import list_stories
from backend.api.auth.me import me
from backend.api.game.start import start

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "user@example.com"


def test_me_403_for_unprovisioned(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="t")
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = me(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403


def test_admin_403_without_administrator_role(request_factory):
    req = request_factory(method="GET", url="/api/manage/stories", token="t")
    entry = MagicMock()
    entry.roles = []

    with patch(
        "backend.api.admin.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)
    ), patch("backend.api.admin.middleware.AccountProvisioningService") as MockService:
        MockService.return_value.authorize_sign_in.return_value = (True, entry)

        response = list_stories(req)

    assert response.status_code == 403


def test_game_403_without_player_role(request_factory):
    req = request_factory(method="POST", url="/api/game/start", token="t")
    entry = MagicMock()
    entry.roles = []
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = start(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403


def test_error_responses_never_expose_oid(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="t")
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = me(req, account_provisioning_service=account_provisioning_service)

    assert USER_OID not in response.get_body().decode()


def test_all_403_responses_use_identical_generic_body_for_provisioning_denial(request_factory):
    req1 = request_factory(method="GET", url="/api/auth/me", token="t")
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = me(req1, account_provisioning_service=account_provisioning_service)

    assert json.loads(response.get_body()) == {"error": "access_denied", "message": "Access not granted"}
