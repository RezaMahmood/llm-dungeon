"""Unit tests for Player role evaluation, mirroring test_admin_capability.py's structure
(006-adventure-and-character-setup research.md Decision 3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.game.middleware import authorize_player

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "user@example.com"


def test_authorize_player_grants_for_player_role(request_factory):
    req = request_factory(method="GET", url="/api/game/adventures", token="valid-token")
    entry = MagicMock()
    entry.roles = ["Player"]
    service = MagicMock()
    service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        is_authorized, user_oid, error = authorize_player(req, account_provisioning_service=service)

    assert is_authorized is True
    assert user_oid == USER_OID
    assert error is None


def test_authorize_player_denies_non_player_role(request_factory):
    req = request_factory(method="GET", url="/api/game/adventures", token="valid-token")
    entry = MagicMock()
    entry.roles = ["Administrator"]
    service = MagicMock()
    service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        is_authorized, _user_oid, error = authorize_player(req, account_provisioning_service=service)

    assert is_authorized is False
    assert error.status_code == 403


def test_authorize_player_denies_non_allowlisted_account(request_factory):
    req = request_factory(method="GET", url="/api/game/adventures", token="valid-token")
    service = MagicMock()
    service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        is_authorized, _user_oid, error = authorize_player(req, account_provisioning_service=service)

    assert is_authorized is False
    assert error.status_code == 403


def test_authorize_player_returns_unauthorized_without_token(request_factory):
    req = request_factory(method="GET", url="/api/game/adventures")

    with patch("backend.api.game.middleware.authenticate_with_email", return_value=(False, None, None, "no token")):
        is_authorized, user_oid, error = authorize_player(req)

    assert is_authorized is False
    assert user_oid is None
    assert error.status_code == 401
