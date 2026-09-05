"""Unit tests for AccountProvisioningService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.services.account_provisioning_service import (
    AccountNotFoundError,
    AccountProvisioningService,
    InvalidEmailError,
    RoleRequiredError,
    SeedAdminRemovalError,
    SelfRemovalError,
)

OID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_OID = "660e8400-e29b-41d4-a716-446655440000"
EMAIL = "player@example.com"


def _entry_dict(**overrides):
    base = {
        "id": EMAIL,
        "email": EMAIL,
        "roles": ["Player"],
        "objectId": None,
        "dateAdded": "2026-08-29T00:00:00Z",
        "addedBy": "admin@example.com",
        "dateBound": None,
        "entityType": "ProvisionedAccountEntry",
    }
    base.update(overrides)
    return base


def _service_with_container():
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    entra = MagicMock()
    return AccountProvisioningService(cosmos_service=cosmos, entra_directory_service=entra), cosmos, container


def _service_with_container_and_entra():
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    entra = MagicMock()
    return AccountProvisioningService(cosmos_service=cosmos, entra_directory_service=entra), container, entra


# --- get_by_email ---


def test_get_by_email_returns_entry_when_found():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict()

    entry = service.get_by_email(EMAIL)

    assert entry.email == EMAIL
    container.read_item.assert_called_once_with(item=EMAIL, partition_key=EMAIL)


def test_get_by_email_lowercases_before_lookup():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict()

    service.get_by_email("Player@Example.com")

    container.read_item.assert_called_once_with(item=EMAIL, partition_key=EMAIL)


def test_get_by_email_returns_none_when_not_found():
    service, _cosmos, container = _service_with_container()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    assert service.get_by_email(EMAIL) is None


def test_get_by_email_does_not_swallow_unexpected_errors():
    """A real Cosmos failure (permissions, network, etc.) must propagate rather than
    being misreported as "no account found" — see function_app._guarded, which logs
    and 500s on exactly this kind of unhandled exception."""
    service, _cosmos, container = _service_with_container()
    container.read_item.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        service.get_by_email(EMAIL)


# --- authorize_sign_in ---


def test_authorize_sign_in_denies_when_no_entry():
    service, _cosmos, container = _service_with_container()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    is_authorized, entry = service.authorize_sign_in(EMAIL, OID)

    assert is_authorized is False
    assert entry is None


def test_authorize_sign_in_denies_without_crashing_when_token_has_no_email_claim():
    """Entra ID's `email` claim isn't guaranteed present on every token — must deny
    cleanly rather than raising AttributeError out of email.lower()."""
    service, _cosmos, container = _service_with_container()

    is_authorized, entry = service.authorize_sign_in(None, OID)

    assert is_authorized is False
    assert entry is None
    container.read_item.assert_not_called()


def test_authorize_sign_in_binds_oid_on_first_sign_in():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict(objectId=None, dateBound=None)

    is_authorized, entry = service.authorize_sign_in(EMAIL, OID)

    assert is_authorized is True
    assert entry.objectId == OID
    assert entry.dateBound is not None
    container.upsert_item.assert_called_once()
    persisted = container.upsert_item.call_args[0][0]
    assert persisted["objectId"] == OID


def test_authorize_sign_in_succeeds_for_matching_bound_oid():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict(objectId=OID, dateBound="2026-08-29T00:05:00Z")

    is_authorized, entry = service.authorize_sign_in(EMAIL, OID)

    assert is_authorized is True
    assert entry.objectId == OID
    container.upsert_item.assert_not_called()


def test_authorize_sign_in_denies_mismatched_bound_oid():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict(objectId=OID, dateBound="2026-08-29T00:05:00Z")

    is_authorized, entry = service.authorize_sign_in(EMAIL, OTHER_OID)

    assert is_authorized is False
    assert entry is None
    container.upsert_item.assert_not_called()


# --- ensure_seed_administrator ---


def test_ensure_seed_administrator_creates_when_absent():
    service, _cosmos, container = _service_with_container()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    service.ensure_seed_administrator(EMAIL)

    container.upsert_item.assert_called_once()
    persisted = container.upsert_item.call_args[0][0]
    assert persisted["email"] == EMAIL
    assert persisted["roles"] == ["Administrator"]
    assert persisted["addedBy"] == "seed"


def test_ensure_seed_administrator_is_a_noop_when_blank():
    service, _cosmos, container = _service_with_container()

    service.ensure_seed_administrator("")

    container.read_item.assert_not_called()
    container.upsert_item.assert_not_called()


def test_ensure_seed_administrator_does_not_overwrite_existing_entry():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict(roles=["Player", "Administrator"])

    service.ensure_seed_administrator(EMAIL)

    container.upsert_item.assert_not_called()


# --- add_or_merge ---


def test_add_or_merge_creates_new_entry():
    service, _cosmos, container = _service_with_container()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    entry = service.add_or_merge(EMAIL, ["Player"], added_by="admin@example.com")

    assert entry.roles == ["Player"]
    assert entry.objectId is None
    container.upsert_item.assert_called_once()


def test_add_or_merge_unions_roles_on_existing_email():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict(roles=["Player"], objectId=OID, dateBound="2026-08-29T00:05:00Z")

    entry = service.add_or_merge(EMAIL, ["Administrator"], added_by="admin@example.com")

    assert sorted(entry.roles) == ["Administrator", "Player"]
    assert entry.objectId == OID
    assert entry.dateBound == "2026-08-29T00:05:00Z"


def test_add_or_merge_rejects_empty_roles():
    service, _cosmos, _container = _service_with_container()

    with pytest.raises(RoleRequiredError):
        service.add_or_merge(EMAIL, [], added_by="admin@example.com")


def test_add_or_merge_rejects_invalid_email():
    service, _cosmos, _container = _service_with_container()

    with pytest.raises(InvalidEmailError):
        service.add_or_merge("not-an-email", ["Player"], added_by="admin@example.com")


def test_add_or_merge_is_a_noop_when_resubmitting_identical_roles():
    service, _cosmos, container = _service_with_container()
    container.read_item.return_value = _entry_dict(roles=["Player"])

    entry = service.add_or_merge(EMAIL, ["Player"], added_by="admin@example.com")

    assert entry.roles == ["Player"]


# --- list_all ---


def test_list_all_returns_every_entry():
    service, cosmos, _container = _service_with_container()
    cosmos.query.return_value = [_entry_dict(), _entry_dict(email="admin@example.com", id="admin@example.com", roles=["Administrator"])]

    entries = service.list_all()

    assert len(entries) == 2
    assert {e.email for e in entries} == {EMAIL, "admin@example.com"}


def test_list_all_sorts_entries_alphabetically_by_email():
    service, cosmos, _container = _service_with_container()
    cosmos.query.return_value = [
        _entry_dict(email="zed@example.com", id="zed@example.com"),
        _entry_dict(email="admin@example.com", id="admin@example.com"),
        _entry_dict(email="mid@example.com", id="mid@example.com"),
    ]

    entries = service.list_all()

    assert [e.email for e in entries] == ["admin@example.com", "mid@example.com", "zed@example.com"]


# --- add_or_merge invites the account's Entra guest user (FR-011, T059) ---


def test_add_or_merge_invites_entra_guest_on_new_entry():
    service, container, entra = _service_with_container_and_entra()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    service.add_or_merge(EMAIL, ["Player"], added_by="admin@example.com")

    entra.invite_guest.assert_called_once_with(EMAIL)


def test_add_or_merge_invites_entra_guest_on_merge():
    service, container, entra = _service_with_container_and_entra()
    container.read_item.return_value = _entry_dict(roles=["Player"], objectId=OID, dateBound="2026-08-29T00:05:00Z")

    service.add_or_merge(EMAIL, ["Administrator"], added_by="admin@example.com")

    entra.invite_guest.assert_called_once_with(EMAIL)


# --- remove_account (FR-012/FR-013, T060) ---

ADMIN_EMAIL = "admin@example.com"
SEED_ADMIN_EMAIL = "seed-admin@example.com"


def test_remove_account_rejects_self_removal():
    service, _container, _entra = _service_with_container_and_entra()

    with pytest.raises(SelfRemovalError):
        service.remove_account(ADMIN_EMAIL, requested_by_email=ADMIN_EMAIL, seed_admin_email=SEED_ADMIN_EMAIL)


def test_remove_account_rejects_seed_administrator_removal():
    service, _container, _entra = _service_with_container_and_entra()

    with pytest.raises(SeedAdminRemovalError):
        service.remove_account(SEED_ADMIN_EMAIL, requested_by_email=ADMIN_EMAIL, seed_admin_email=SEED_ADMIN_EMAIL)


def test_remove_account_raises_not_found_when_no_entry_exists():
    service, container, _entra = _service_with_container_and_entra()
    container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")

    with pytest.raises(AccountNotFoundError):
        service.remove_account(EMAIL, requested_by_email=ADMIN_EMAIL, seed_admin_email=SEED_ADMIN_EMAIL)


def test_remove_account_deletes_entry_and_removes_entra_guest():
    service, container, entra = _service_with_container_and_entra()
    container.read_item.return_value = _entry_dict()

    service.remove_account(EMAIL, requested_by_email=ADMIN_EMAIL, seed_admin_email=SEED_ADMIN_EMAIL)

    container.delete_item.assert_called_once_with(item=EMAIL, partition_key=EMAIL)
    entra.remove_guest.assert_called_once_with(EMAIL)
