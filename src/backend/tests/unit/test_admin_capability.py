"""Unit tests for Administrator role evaluation (User Story 2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.services.account_provisioning_service import AccountProvisioningService

OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "user@example.com"


def _service_with_entry(roles: list[str]):
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    container.read_item.return_value = {
        "id": EMAIL,
        "email": EMAIL,
        "roles": roles,
        "objectId": OID,
        "dateAdded": "2026-08-29T00:00:00Z",
        "addedBy": "admin@example.com",
        "dateBound": "2026-08-29T00:05:00Z",
        "entityType": "ProvisionedAccountEntry",
    }
    return AccountProvisioningService(cosmos_service=cosmos)


def test_authorize_sign_in_grants_administrator_role_for_admin_entry():
    service = _service_with_entry(["Administrator"])

    is_authorized, entry = service.authorize_sign_in(EMAIL, OID)

    assert is_authorized is True
    assert "Administrator" in entry.roles


def test_authorize_sign_in_administrator_role_true_for_admin_false_for_player():
    admin_service = _service_with_entry(["Administrator"])
    player_service = _service_with_entry(["Player"])

    _is_authorized, admin_entry = admin_service.authorize_sign_in(EMAIL, OID)
    _is_authorized, player_entry = player_service.authorize_sign_in(EMAIL, OID)

    assert "Administrator" in admin_entry.roles
    assert "Administrator" not in player_entry.roles
