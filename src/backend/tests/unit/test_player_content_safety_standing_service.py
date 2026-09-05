"""Unit tests for PlayerContentSafetyStandingService (008-core-gameplay research.md
Decision 9, FR-013). Cosmos is faked in-memory, matching this repo's other unit tests."""

from __future__ import annotations

import datetime

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.services.player_content_safety_standing_service import PlayerContentSafetyStandingService

PLAYER_ID = "oid-1"


class FakeContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self._etag_counter = 0

    def _next_etag(self) -> str:
        self._etag_counter += 1
        return f"etag-{self._etag_counter}"

    def read_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        return self.items[item]

    def create_item(self, body):
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[body["id"]] = body
        return body

    def replace_item(self, item, body, etag=None, match_condition=None):  # noqa: ARG002
        current = self.items.get(item)
        if match_condition == MatchConditions.IfNotModified and current is not None and current["_etag"] != etag:
            raise CosmosAccessConditionFailedError
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[item] = body
        return body


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())


def _service() -> PlayerContentSafetyStandingService:
    return PlayerContentSafetyStandingService(cosmos_service=FakeCosmosService())


def test_first_flag_creates_document_with_count_one_and_no_lockout():
    service = _service()

    standing = service.record_flag(PLAYER_ID)

    assert standing.flaggedCount == 1
    assert standing.lockoutUntil is None
    assert service.is_locked_out(PLAYER_ID) is False


def test_third_flag_sets_lockout_one_hour_out():
    service = _service()
    service.record_flag(PLAYER_ID)
    service.record_flag(PLAYER_ID)

    standing = service.record_flag(PLAYER_ID)

    assert standing.flaggedCount == 3
    assert standing.lockoutUntil is not None
    assert service.is_locked_out(PLAYER_ID) is True


def test_is_locked_out_false_once_lockout_expires():
    service = _service()
    for _ in range(3):
        service.record_flag(PLAYER_ID)

    container = service._container()  # noqa: SLF001 - test-only introspection
    item = container.items[PLAYER_ID]
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    item["lockoutUntil"] = past.strftime("%Y-%m-%dT%H:%M:%SZ")

    assert service.is_locked_out(PLAYER_ID) is False


def test_fourth_flag_after_expiry_does_not_reset_count_and_issues_fresh_lockout():
    service = _service()
    for _ in range(3):
        service.record_flag(PLAYER_ID)

    container = service._container()  # noqa: SLF001 - test-only introspection
    item = container.items[PLAYER_ID]
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    item["lockoutUntil"] = past.strftime("%Y-%m-%dT%H:%M:%SZ")
    item["_etag"] = "etag-stale-bump"
    container.items[PLAYER_ID] = item

    standing = service.record_flag(PLAYER_ID)

    assert standing.flaggedCount == 4
    assert standing.lockoutUntil is not None
    assert service.is_locked_out(PLAYER_ID) is True
