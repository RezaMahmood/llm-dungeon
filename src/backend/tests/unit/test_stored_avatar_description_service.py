"""Unit tests for StoredAvatarDescriptionService (034-avatar-memory-and-visibility
research.md Decision 1). Cosmos is faked in-memory, matching this repo's other unit
tests."""

from __future__ import annotations

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.services.stored_avatar_description_service import StoredAvatarDescriptionService

PLAYER_ID = "oid-1"
OTHER_PLAYER_ID = "oid-2"
STORY_ID = "story-1"
OTHER_STORY_ID = "story-2"


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

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        rows = list(self.get_container(container_name).items.values())
        param_map = {p["name"]: p["value"] for p in (params or [])}
        if "c.storyId = @storyId" in sql:
            rows = [r for r in rows if r.get("storyId") == param_map.get("@storyId")]
        return rows


def _service() -> tuple[StoredAvatarDescriptionService, FakeCosmosService]:
    cosmos = FakeCosmosService()
    return StoredAvatarDescriptionService(cosmos_service=cosmos), cosmos


def test_get_returns_none_when_nothing_stored():
    service, _cosmos = _service()

    assert service.get(PLAYER_ID, STORY_ID) is None


def test_store_then_get_round_trips():
    service, _cosmos = _service()

    service.store(PLAYER_ID, STORY_ID, "A one-eyed lighthouse keeper.")

    assert service.get(PLAYER_ID, STORY_ID) == "A one-eyed lighthouse keeper."


def test_second_store_replaces_rather_than_accumulates():
    service, cosmos = _service()

    service.store(PLAYER_ID, STORY_ID, "First description.")
    service.store(PLAYER_ID, STORY_ID, "Second, replacing description.")

    assert service.get(PLAYER_ID, STORY_ID) == "Second, replacing description."
    container = cosmos.get_container("storedAvatarDescriptions")
    assert len(container.items) == 1


def test_stored_descriptions_are_isolated_per_player_and_per_story():
    service, _cosmos = _service()

    service.store(PLAYER_ID, STORY_ID, "Player one's description.")
    service.store(OTHER_PLAYER_ID, STORY_ID, "Player two's description.")
    service.store(PLAYER_ID, OTHER_STORY_ID, "Player one's other-story description.")

    assert service.get(PLAYER_ID, STORY_ID) == "Player one's description."
    assert service.get(OTHER_PLAYER_ID, STORY_ID) == "Player two's description."
    assert service.get(PLAYER_ID, OTHER_STORY_ID) == "Player one's other-story description."


def test_delete_for_story_removes_only_rows_for_that_story():
    service, cosmos = _service()
    service.store(PLAYER_ID, STORY_ID, "Description for story one.")
    service.store(OTHER_PLAYER_ID, STORY_ID, "Another player's description for story one.")
    service.store(PLAYER_ID, OTHER_STORY_ID, "Description for story two.")

    removed = service.delete_for_story(STORY_ID)

    assert removed == 2
    assert service.get(PLAYER_ID, STORY_ID) is None
    assert service.get(OTHER_PLAYER_ID, STORY_ID) is None
    assert service.get(PLAYER_ID, OTHER_STORY_ID) == "Description for story two."


def test_delete_for_story_tolerates_no_stored_rows():
    service, _cosmos = _service()

    assert service.delete_for_story("story-with-nothing-stored") == 0
