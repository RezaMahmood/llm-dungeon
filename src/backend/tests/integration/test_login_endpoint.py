"""Integration tests for POST /api/auth/login."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.auth.login import login
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
    """A real AccountProvisioningService over a mocked Cosmos container and a
    mocked EntraDirectoryService, so authorize_sign_in's bind logic runs for
    real against test doubles without making any real Graph calls."""
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    entra = MagicMock()
    return AccountProvisioningService(cosmos_service=cosmos, entra_directory_service=entra), container


def test_login_valid_token_provisioned_player_returns_200(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    entry = ProvisionedAccountEntry(email="player@example.com", roles=["Player"], objectId=USER_OID)
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.auth.login.authenticate_with_email", return_value=(True, USER_OID, "player@example.com", None)):
        response = login(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 200
    body = response.get_body().decode()
    assert '"hasPlayer": true' in body or '"hasPlayer":true' in body
    assert '"hasAdministrator": false' in body or '"hasAdministrator":false' in body


def test_login_valid_token_unprovisioned_returns_403(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (False, None)

    with patch("backend.api.auth.login.authenticate_with_email", return_value=(True, USER_OID, "nobody@example.com", None)):
        response = login(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403


def test_login_expired_token_returns_401(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="expired-token")

    with patch("backend.api.auth.login.authenticate_with_email", return_value=(False, None, None, "Invalid or expired token")):
        response = login(req)

    assert response.status_code == 401
    assert "Invalid or expired token" in response.get_body().decode()


# --- Scenario 1: seed administrator bootstraps and binds (User Story 1) ---


def test_seed_administrator_first_sign_in_succeeds_and_binds_object_id(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=None, dateBound=None)

    with patch("backend.api.auth.login.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 200
    persisted = container.upsert_item.call_args[0][0]
    assert persisted["objectId"] == USER_OID
    assert persisted["dateBound"] is not None


def test_any_other_email_is_denied_before_further_accounts_exist(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    with patch(
        "backend.api.auth.login.authenticate_with_email", return_value=(True, USER_OID, "someone.else@example.com", None)
    ):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 403


def test_second_sign_in_with_matching_bound_object_id_succeeds(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=USER_OID, dateBound="2026-08-29T00:05:00Z")

    with patch("backend.api.auth.login.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 200
    container.upsert_item.assert_not_called()


def test_sign_in_matches_regardless_of_token_email_letter_case(request_factory):
    """FR-008/SC-005: a token's email claim can arrive in any casing (Microsoft
    does not guarantee lowercase); matching against the lowercase-stored entry
    must still succeed end-to-end through the login endpoint."""
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=USER_OID, dateBound="2026-08-29T00:05:00Z")

    with patch(
        "backend.api.auth.login.authenticate_with_email",
        return_value=(True, USER_OID, "Admin@Example.com", None),
    ):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 200
    container.read_item.assert_called_once_with(item=EMAIL, partition_key=EMAIL)


def test_second_sign_in_with_mismatched_object_id_is_denied(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=USER_OID, dateBound="2026-08-29T00:05:00Z")

    with patch("backend.api.auth.login.authenticate_with_email", return_value=(True, OTHER_OID, EMAIL, None)):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 403
    container.upsert_item.assert_not_called()


# --- Ties US2's add flow to US1's sign-in flow (T024) ---


def test_newly_added_account_can_subsequently_sign_in_and_binds_object_id(request_factory):
    """An email added via POST /api/manage/accounts (add_or_merge) can then sign in
    and bind its objectId on that first sign-in."""
    service, container = _real_service_with_container()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    added_entry = service.add_or_merge("newplayer@example.com", ["Player"], added_by="admin@example.com")
    assert added_entry.objectId is None

    # Simulate the persisted entry now existing for the sign-in lookup.
    container.read_item.side_effect = None
    container.read_item.return_value = added_entry.to_dict()

    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    with patch(
        "backend.api.auth.login.authenticate_with_email",
        return_value=(True, USER_OID, "newplayer@example.com", None),
    ):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 200
    persisted = container.upsert_item.call_args[0][0]
    assert persisted["objectId"] == USER_OID


# --- A removed account is denied sign-in immediately after removal (T069, FR-012/FR-013) ---


def test_removed_account_is_denied_sign_in(request_factory):
    service, container = _real_service_with_container()
    container.read_item.return_value = _entry_dict(objectId=USER_OID, dateBound="2026-08-29T00:05:00Z")

    service.remove_account(EMAIL, requested_by_email="other-admin@example.com", seed_admin_email="")

    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")
    with patch(
        "backend.api.auth.login.authenticate_with_email",
        return_value=(True, USER_OID, EMAIL, None),
    ):
        response = login(req, account_provisioning_service=service)

    assert response.status_code == 403
