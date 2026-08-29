"""Unit tests for Administrator capability evaluation (User Story 2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.capability_service import CapabilityService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def _service_with_capabilities(capabilities: list[str]):
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {"user_oid": USER_OID, "capability": cap, "dateRevoked": None} for cap in capabilities
    ]
    return CapabilityService(cosmos_service=cosmos)


def test_get_user_capabilities_returns_administrator_for_admin_user():
    service = _service_with_capabilities(["Administrator"])

    assert service.get_user_capabilities(USER_OID) == {"Administrator"}


def test_has_capability_administrator_true_for_admin_false_for_player():
    admin_service = _service_with_capabilities(["Administrator"])
    player_service = _service_with_capabilities(["Player"])

    assert admin_service.has_capability(USER_OID, "Administrator") is True
    assert player_service.has_capability(USER_OID, "Administrator") is False
