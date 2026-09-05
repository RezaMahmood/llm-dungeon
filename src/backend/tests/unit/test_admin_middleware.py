"""Unit tests for Administrator role evaluation, mirroring test_game_middleware.py's
structure (006-adventure-and-character-setup research.md Decision 3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.admin.middleware import authorize_admin

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "admin@example.com"


def test_authorize_admin_grants_for_administrator_role(request_factory):
    req = request_factory(method="GET", url="/api/manage/accounts", token="valid-token")
    entry = MagicMock()
    entry.roles = ["Administrator"]
    service = MagicMock()
    service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.admin.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        is_authorized, user_oid, error = authorize_admin(req, account_provisioning_service=service)

    assert is_authorized is True
    assert user_oid == USER_OID
    assert error is None


def test_authorize_admin_denies_non_administrator_role(request_factory):
    req = request_factory(method="GET", url="/api/manage/accounts", token="valid-token")
    entry = MagicMock()
    entry.roles = ["Player"]
    service = MagicMock()
    service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.admin.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        is_authorized, _user_oid, error = authorize_admin(req, account_provisioning_service=service)

    assert is_authorized is False
    assert error.status_code == 403


def test_authorize_admin_denies_non_allowlisted_account(request_factory):
    req = request_factory(method="GET", url="/api/manage/accounts", token="valid-token")
    service = MagicMock()
    service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.admin.middleware.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        is_authorized, _user_oid, error = authorize_admin(req, account_provisioning_service=service)

    assert is_authorized is False
    assert error.status_code == 403


def test_authorize_admin_returns_unauthorized_without_token(request_factory):
    req = request_factory(method="GET", url="/api/manage/accounts")

    with patch("backend.api.admin.middleware.authenticate_with_email", return_value=(False, None, None, "no token")):
        is_authorized, user_oid, error = authorize_admin(req)

    assert is_authorized is False
    assert user_oid is None
    assert error.status_code == 401


def test_authorize_admin_forwards_the_auth_failure_message(request_factory):
    """#212/#217: the 401 response must carry the specific reason
    authenticate_with_email() gave, not always the same generic default."""
    req = request_factory(method="GET", url="/api/manage/accounts", token="bad-token")

    with patch(
        "backend.api.admin.middleware.authenticate_with_email",
        return_value=(False, None, None, "Invalid or expired token"),
    ):
        _is_authorized, _user_oid, error = authorize_admin(req)

    assert error.status_code == 401
    assert "Invalid or expired token" in error.get_body().decode()
