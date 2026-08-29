"""Unit tests for AllowListService."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.allow_list_service import AllowListService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def _service_with_query_result(rows):
    cosmos = MagicMock()
    cosmos.query.return_value = rows
    return AllowListService(cosmos_service=cosmos), cosmos


def test_is_allowed_for_allow_listed_user_returns_true():
    entry = {
        "id": USER_OID,
        "user_oid": USER_OID,
        "email": "player@example.com",
        "dateAdded": "2026-08-28T20:00:00Z",
        "dateRemoved": None,
        "entityType": "AllowListEntry",
    }
    service, _cosmos = _service_with_query_result([entry])

    assert service.is_allowed(USER_OID) is True


def test_is_allowed_for_not_allow_listed_user_returns_false():
    service, _cosmos = _service_with_query_result([])

    assert service.is_allowed(USER_OID) is False


def test_is_allowed_for_soft_deleted_user_returns_false():
    # The Cosmos query itself filters dateRemoved = null, so a soft-deleted
    # entry never comes back in the result set.
    service, cosmos = _service_with_query_result([])

    result = service.is_allowed(USER_OID)

    assert result is False
    cosmos.query.assert_called_once()


def test_get_allow_list_entry_returns_none_when_not_found():
    service, _cosmos = _service_with_query_result([])

    assert service.get_allow_list_entry(USER_OID) is None
