"""Integration tests for GET /api/auth/me."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.me import me
from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.services.account_provisioning_service import AccountProvisioningService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_OID = "660e8400-e29b-41d4-a716-446655440000"
EMAIL = "admin@example.com"


def _entry_dict(**overrides):
    base = {
        "id": EMAIL,
        "email": EMAIL,
        "roles": ["Administrator"],
        "objectId": None,
        "dateAdded": "2026-08-29T00:00:00Z",
        "addedBy": "seed",
        "dateBound": None,
        "entityType": "ProvisionedAccountEntry",
    }
    base.update(overrides)
    return base


def _real_service_with_container():
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    return AccountProvisioningService(cosmos_service=cosmos), container


def test_me_valid_player_token_returns_200_with_capabilities(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    entry = ProvisionedAccountEntry(email="player@example.com", roles=["Player"], objectId=USER_OID)
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, "player@example.com", None)):
        response = me(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 200
    assert USER_OID in response.get_body().decode()


def test_me_expired_token_returns_401(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="expired-token")

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(False, None, None, "Invalid or expired token")):
        response = me(req)

    assert response.status_code == 401
    # #212: the endpoint previously always returned the generic "No valid
    # authentication token provided" message regardless of *why* validation
    # failed, discarding middleware's already-generic (non-account-revealing)
    # distinction between "missing" and "present but invalid" — collapsing
    # a genuine token-validation failure and a missing-token request into an
    # identical response, which made diagnosing #212 in production impossible.
    assert "Invalid or expired token" in response.get_body().decode()


def test_me_unprovisioned_returns_403(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, "nobody@example.com", None)):
        response = me(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403


# --- Mirrors test_login_endpoint.py's bind/match/mismatch cases for /api/auth/me ---


def test_seed_administrator_first_call_binds_object_id(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=None, dateBound=None)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = me(req, account_provisioning_service=service)

    assert response.status_code == 200
    persisted = container.upsert_item.call_args[0][0]
    assert persisted["objectId"] == USER_OID


def test_matching_bound_object_id_succeeds(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=USER_OID, dateBound="2026-08-29T00:05:00Z")

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = me(req, account_provisioning_service=service)

    assert response.status_code == 200
    container.upsert_item.assert_not_called()


def test_mismatched_object_id_is_denied(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=USER_OID, dateBound="2026-08-29T00:05:00Z")

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, OTHER_OID, EMAIL, None)):
        response = me(req, account_provisioning_service=service)

    assert response.status_code == 403
    container.upsert_item.assert_not_called()
