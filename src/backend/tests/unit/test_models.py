"""Unit tests for ProvisionedAccountEntry model validation."""

from __future__ import annotations

import pytest

from backend.models.provisioned_account_entry import ProvisionedAccountEntry


def test_provisioned_account_entry_rejects_empty_roles():
    with pytest.raises(ValueError):
        ProvisionedAccountEntry(email="player@example.com", roles=[])


def test_provisioned_account_entry_rejects_unrecognized_role():
    with pytest.raises(ValueError):
        ProvisionedAccountEntry(email="player@example.com", roles=["SuperAdmin"])


def test_provisioned_account_entry_lowercases_email_and_id():
    entry = ProvisionedAccountEntry(email="Player@Example.com", roles=["Player"])
    assert entry.email == "player@example.com"
    assert entry.id == "player@example.com"


def test_provisioned_account_entry_id_matches_email_when_explicit():
    entry = ProvisionedAccountEntry(email="Player@Example.com", roles=["Player"], id="Player@Example.com")
    assert entry.id == entry.email == "player@example.com"


def test_provisioned_account_entry_round_trips_through_dict():
    entry = ProvisionedAccountEntry(
        email="admin@example.com",
        roles=["Administrator"],
        objectId="oid-1",
        dateAdded="2026-08-29T00:00:00Z",
        addedBy="seed",
        dateBound="2026-08-29T00:05:00Z",
    )
    restored = ProvisionedAccountEntry.from_dict(entry.to_dict())
    assert restored == entry
