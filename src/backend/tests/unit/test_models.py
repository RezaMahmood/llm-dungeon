"""Unit tests for AllowListEntry and CapabilityAssignment model validation."""

from __future__ import annotations

import pytest

from backend.models.allow_list_entry import AllowListEntry
from backend.models.capability_assignment import CapabilityAssignment

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_allow_list_entry_requires_user_oid():
    with pytest.raises(ValueError):
        AllowListEntry(user_oid="")


def test_allow_list_entry_id_defaults_to_user_oid():
    entry = AllowListEntry(user_oid=USER_OID)
    assert entry.id == USER_OID


def test_allow_list_entry_is_active_when_not_removed():
    entry = AllowListEntry(user_oid=USER_OID)
    assert entry.is_active() is True


def test_allow_list_entry_is_inactive_when_removed():
    entry = AllowListEntry(user_oid=USER_OID, dateRemoved="2026-08-29T00:00:00Z")
    assert entry.is_active() is False


def test_capability_assignment_rejects_invalid_capability():
    with pytest.raises(ValueError):
        CapabilityAssignment(user_oid=USER_OID, capability="SuperAdmin")


def test_capability_assignment_id_is_composite():
    assignment = CapabilityAssignment(user_oid=USER_OID, capability="Player")
    assert assignment.id == f"capability-{USER_OID}-Player"


def test_capability_assignment_active_states():
    active = CapabilityAssignment(user_oid=USER_OID, capability="Player")
    revoked = CapabilityAssignment(user_oid=USER_OID, capability="Administrator", dateRevoked="2026-08-29T00:00:00Z")

    assert active.is_active() is True
    assert revoked.is_active() is False


def test_capability_assignment_round_trips_through_dict():
    assignment = CapabilityAssignment(user_oid=USER_OID, capability="Player", assignedBy="admin@example.com")
    restored = CapabilityAssignment.from_dict(assignment.to_dict())
    assert restored == assignment
