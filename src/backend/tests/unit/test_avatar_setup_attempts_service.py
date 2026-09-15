"""Unit tests for AvatarSetupAttemptsService (032-story-archetypes-player-avatar research.md
Decision 3). Cosmos is faked in-memory, matching this repo's other unit tests."""

from __future__ import annotations

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.services.avatar_setup_attempts_service import AvatarSetupAttemptsService

PLAYER_ID = "oid-1"
STORY_ID = "story-1"


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

    def delete_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        del self.items[item]


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())


def _service() -> AvatarSetupAttemptsService:
    return AvatarSetupAttemptsService(cosmos_service=FakeCosmosService())


def test_get_attempts_is_zero_for_an_untouched_pair():
    service = _service()

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 0


def test_record_attempt_creates_the_document_on_the_first_call():
    service = _service()

    count = service.record_attempt(PLAYER_ID, STORY_ID)

    assert count == 1
    assert service.get_attempts(PLAYER_ID, STORY_ID) == 1


def test_record_attempt_increments_on_repeated_calls():
    service = _service()

    service.record_attempt(PLAYER_ID, STORY_ID)
    service.record_attempt(PLAYER_ID, STORY_ID)
    count = service.record_attempt(PLAYER_ID, STORY_ID)

    assert count == 3


def test_attempts_are_scoped_per_player_and_story():
    service = _service()

    service.record_attempt(PLAYER_ID, STORY_ID)
    service.record_attempt(PLAYER_ID, "story-2")
    service.record_attempt("oid-2", STORY_ID)

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 1
    assert service.get_attempts(PLAYER_ID, "story-2") == 1
    assert service.get_attempts("oid-2", STORY_ID) == 1


def test_clear_removes_the_document_so_a_later_setup_starts_fresh():
    service = _service()
    service.record_attempt(PLAYER_ID, STORY_ID)

    service.clear(PLAYER_ID, STORY_ID)

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 0


def test_clear_is_a_no_op_when_no_document_exists():
    service = _service()

    service.clear(PLAYER_ID, STORY_ID)  # must not raise

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 0
