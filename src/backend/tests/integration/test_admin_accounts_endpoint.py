"""Integration tests for POST /api/manage/accounts and GET /api/manage/accounts."""

from __future__ import annotations

import json
from unittest.mock import ANY, MagicMock, patch

from backend.api.admin.accounts import add_account, list_accounts, remove_account
from backend.models.provisioned_account_entry import ProvisionedAccountEntry

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"
ADMIN_EMAIL = "admin@example.com"


def _authorized_request(request_factory, method="POST", url="/api/manage/accounts", body=b""):
    return request_factory(method=method, url=url, token="valid-token", body=body)


def _patched_authorize_admin(entry_roles=("Administrator",)):
    entry = MagicMock()
    entry.roles = list(entry_roles)
    return patch(
        "backend.api.admin.accounts.authorize_admin",
        return_value=(True, ADMIN_OID, None),
    ), patch(
        "backend.api.admin.accounts.authenticate_with_email",
        return_value=(True, ADMIN_OID, ADMIN_EMAIL, None),
    )


# --- POST /api/manage/accounts (User Story 2) ---


def test_add_account_creates_entry_with_player_role(request_factory):
    req = _authorized_request(request_factory, body=json.dumps({"email": "player@example.com", "roles": ["Player"]}).encode())
    service = MagicMock()
    service.add_or_merge.return_value = ProvisionedAccountEntry(email="player@example.com", roles=["Player"])

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = add_account(req, account_provisioning_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["account"] == {"email": "player@example.com", "roles": ["Player"], "bound": False, "isSeedAdmin": False}
    service.add_or_merge.assert_called_once_with("player@example.com", ["Player"], added_by=ADMIN_EMAIL)


def test_add_account_creates_entry_with_administrator_role(request_factory):
    req = _authorized_request(request_factory, body=json.dumps({"email": "newadmin@example.com", "roles": ["Administrator"]}).encode())
    service = MagicMock()
    service.add_or_merge.return_value = ProvisionedAccountEntry(email="newadmin@example.com", roles=["Administrator"])

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = add_account(req, account_provisioning_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["account"]["roles"] == ["Administrator"]


def test_add_account_creates_entry_with_both_roles(request_factory):
    req = _authorized_request(
        request_factory, body=json.dumps({"email": "dual@example.com", "roles": ["Player", "Administrator"]}).encode()
    )
    service = MagicMock()
    service.add_or_merge.return_value = ProvisionedAccountEntry(email="dual@example.com", roles=["Administrator", "Player"])

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = add_account(req, account_provisioning_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert sorted(body["account"]["roles"]) == ["Administrator", "Player"]


def test_add_account_returns_400_role_required_for_empty_roles(request_factory):
    from backend.services.account_provisioning_service import RoleRequiredError

    req = _authorized_request(request_factory, body=json.dumps({"email": "someone@example.com", "roles": []}).encode())
    service = MagicMock()
    service.add_or_merge.side_effect = RoleRequiredError("roles required")

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = add_account(req, account_provisioning_service=service)

    assert response.status_code == 400
    assert json.loads(response.get_body())["error"] == "role_required"


def test_add_account_returns_400_invalid_email_for_malformed_email(request_factory):
    from backend.services.account_provisioning_service import InvalidEmailError

    req = _authorized_request(request_factory, body=json.dumps({"email": "not-an-email", "roles": ["Player"]}).encode())
    service = MagicMock()
    service.add_or_merge.side_effect = InvalidEmailError("bad email")

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = add_account(req, account_provisioning_service=service)

    assert response.status_code == 400
    assert json.loads(response.get_body())["error"] == "invalid_email"


def test_add_account_returns_403_for_non_administrator(request_factory):
    req = _authorized_request(request_factory, body=json.dumps({"email": "x@example.com", "roles": ["Player"]}).encode())
    service = MagicMock()

    with patch("backend.api.admin.accounts.authorize_admin", return_value=(False, ADMIN_OID, MagicMock(status_code=403))):
        response = add_account(req, account_provisioning_service=service)

    assert response.status_code == 403


# --- Re-adding merges roles into one entry (User Story 3) ---


def test_add_account_merges_roles_into_existing_entry(request_factory):
    req = _authorized_request(
        request_factory, body=json.dumps({"email": "player@example.com", "roles": ["Administrator"]}).encode()
    )
    service = MagicMock()
    service.add_or_merge.return_value = ProvisionedAccountEntry(
        email="player@example.com", roles=["Administrator", "Player"], objectId="oid-1"
    )

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = add_account(req, account_provisioning_service=service)

    body = json.loads(response.get_body())
    assert sorted(body["account"]["roles"]) == ["Administrator", "Player"]
    assert body["account"]["bound"] is True


def test_resubmitting_identical_request_twice_is_a_no_op(request_factory):
    req = _authorized_request(request_factory, body=json.dumps({"email": "player@example.com", "roles": ["Player"]}).encode())
    service = MagicMock()
    service.add_or_merge.return_value = ProvisionedAccountEntry(email="player@example.com", roles=["Player"])

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response1 = add_account(req, account_provisioning_service=service)
        response2 = add_account(req, account_provisioning_service=service)

    assert response1.status_code == response2.status_code == 200
    assert json.loads(response1.get_body()) == json.loads(response2.get_body())


# --- GET /api/manage/accounts (User Story 3) ---


def test_list_accounts_returns_every_entry_with_email_and_roles(request_factory):
    req = request_factory(method="GET", url="/api/manage/accounts", token="valid-token")
    service = MagicMock()
    service.list_all.return_value = [
        ProvisionedAccountEntry(email="admin@example.com", roles=["Administrator"], objectId="oid-1"),
        ProvisionedAccountEntry(email="player@example.com", roles=["Player"]),
    ]

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = list_accounts(req, account_provisioning_service=service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["accounts"] == [
        {"email": "admin@example.com", "roles": ["Administrator"], "bound": True, "isSeedAdmin": False},
        {"email": "player@example.com", "roles": ["Player"], "bound": False, "isSeedAdmin": False},
    ]


def test_list_accounts_marks_the_seed_administrator_entry(request_factory, monkeypatch):
    monkeypatch.setattr("backend.api.admin.accounts.config.SEED_ADMIN_EMAIL", "admin@example.com")
    req = request_factory(method="GET", url="/api/manage/accounts", token="valid-token")
    service = MagicMock()
    service.list_all.return_value = [ProvisionedAccountEntry(email="admin@example.com", roles=["Administrator"], objectId="oid-1")]

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = list_accounts(req, account_provisioning_service=service)

    body = json.loads(response.get_body())
    assert body["accounts"][0]["isSeedAdmin"] is True


def test_list_accounts_returns_403_for_non_administrator(request_factory):
    req = request_factory(method="GET", url="/api/manage/accounts", token="valid-token")
    service = MagicMock()

    with patch("backend.api.admin.accounts.authorize_admin", return_value=(False, ADMIN_OID, MagicMock(status_code=403))):
        response = list_accounts(req, account_provisioning_service=service)

    assert response.status_code == 403


# --- DELETE /api/manage/accounts (User Story: Removal, T068) ---


def _delete_request(request_factory, email="player@example.com"):
    return request_factory(
        method="DELETE",
        url="/api/manage/accounts",
        token="valid-token",
        body=json.dumps({"email": email}).encode(),
    )


def test_remove_account_returns_200_on_success(request_factory):
    req = _delete_request(request_factory)
    service = MagicMock()

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = remove_account(req, account_provisioning_service=service)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"status": "success"}
    service.remove_account.assert_called_once_with(
        "player@example.com", requested_by_email=ADMIN_EMAIL, seed_admin_email=ANY
    )


def test_remove_account_returns_400_self_removal(request_factory):
    from backend.services.account_provisioning_service import SelfRemovalError

    req = _delete_request(request_factory, email=ADMIN_EMAIL)
    service = MagicMock()
    service.remove_account.side_effect = SelfRemovalError("self removal")

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = remove_account(req, account_provisioning_service=service)

    assert response.status_code == 400
    assert json.loads(response.get_body())["error"] == "self_removal"


def test_remove_account_returns_400_seed_admin_removal(request_factory):
    from backend.services.account_provisioning_service import SeedAdminRemovalError

    req = _delete_request(request_factory, email="seed-admin@example.com")
    service = MagicMock()
    service.remove_account.side_effect = SeedAdminRemovalError("seed admin removal")

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = remove_account(req, account_provisioning_service=service)

    assert response.status_code == 400
    assert json.loads(response.get_body())["error"] == "seed_admin_removal"


def test_remove_account_returns_404_not_found(request_factory):
    from backend.services.account_provisioning_service import AccountNotFoundError

    req = _delete_request(request_factory, email="nobody@example.com")
    service = MagicMock()
    service.remove_account.side_effect = AccountNotFoundError("not found")

    authorize_patch, email_patch = _patched_authorize_admin()
    with authorize_patch, email_patch:
        response = remove_account(req, account_provisioning_service=service)

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "not_found"


def test_remove_account_returns_403_for_non_administrator(request_factory):
    req = _delete_request(request_factory)
    service = MagicMock()

    with patch("backend.api.admin.accounts.authorize_admin", return_value=(False, ADMIN_OID, MagicMock(status_code=403))):
        response = remove_account(req, account_provisioning_service=service)

    assert response.status_code == 403
