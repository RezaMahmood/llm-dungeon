"""Unit tests for AccountProvisioningService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.services.account_provisioning_service import (
    AccountProvisioningService,
    InvalidEmailError,
    RoleRequiredError,
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
    return AccountProvisioningService(cosmos_service=cosmos), cosmos, container


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
    container.read_item.side_effect = Exception("not found")

    assert service.get_by_email(EMAIL) is None


# --- authorize_sign_in ---


def test_authorize_sign_in_denies_when_no_entry():
    service, _cosmos, container = _service_with_container()
    container.read_item.side_effect = Exception("not found")

    is_authorized, entry = service.authorize_sign_in(EMAIL, OID)

    assert is_authorized is False
    assert entry is None


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
    container.read_item.side_effect = Exception("not found")

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
    container.read_item.side_effect = Exception("not found")

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
