"""Unit tests for CapabilityService."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.capability_service import CapabilityService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def _service_with_capabilities(capabilities: list[str]):
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {"user_oid": USER_OID, "capability": cap, "dateRevoked": None} for cap in capabilities
    ]
    return CapabilityService(cosmos_service=cosmos), cosmos


def test_get_user_capabilities_for_player_only():
    service, _cosmos = _service_with_capabilities(["Player"])

    assert service.get_user_capabilities(USER_OID) == {"Player"}


def test_get_user_capabilities_for_both_roles():
    service, _cosmos = _service_with_capabilities(["Player", "Administrator"])

    assert service.get_user_capabilities(USER_OID) == {"Player", "Administrator"}


def test_get_user_capabilities_for_no_roles():
    service, _cosmos = _service_with_capabilities([])

    assert service.get_user_capabilities(USER_OID) == set()


def test_has_capability_true_and_false():
    service, _cosmos = _service_with_capabilities(["Player"])

    assert service.has_capability(USER_OID, "Player") is True
    assert service.has_capability(USER_OID, "Administrator") is False


def test_get_user_capabilities_is_cached_per_instance():
    service, cosmos = _service_with_capabilities(["Player"])

    service.get_user_capabilities(USER_OID)
    service.get_user_capabilities(USER_OID)

    cosmos.query.assert_called_once()
