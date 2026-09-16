"""Unit tests for AvatarSetupAttemptsService (032-story-archetypes-player-avatar research.md
Decision 3). Cosmos is faked in-memory, matching this repo's other unit tests."""

from __future__ import annotations

import datetime

import pytest
from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.config import config
from backend.services.avatar_setup_attempts_service import ATTEMPT_WINDOW, AvatarSetupAttemptsService

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


def _service_with_cosmos() -> tuple[AvatarSetupAttemptsService, FakeCosmosService]:
    cosmos = FakeCosmosService()
    return AvatarSetupAttemptsService(cosmos_service=cosmos), cosmos


def _age_the_window(cosmos: FakeCosmosService, player_id: str, story_id: str, past: datetime.timedelta) -> None:
    """Backdate a stored counting window so it reads as lapsed, without waiting out
    ATTEMPT_WINDOW in real time."""
    doc = cosmos.get_container(config.AVATAR_SETUP_ATTEMPTS_CONTAINER).items[f"{player_id}:{story_id}"]
    started = datetime.datetime.now(datetime.timezone.utc) - past
    doc["windowStartedAt"] = started.strftime("%Y-%m-%dT%H:%M:%SZ")


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


# --- Rolling attempt window (issue #361 convergence, FR-014) ---


def test_attempts_inside_the_window_still_accumulate():
    """The guard rail itself is unchanged: sustained probing within one window is capped."""
    service, cosmos = _service_with_cosmos()

    service.record_attempt(PLAYER_ID, STORY_ID)
    service.record_attempt(PLAYER_ID, STORY_ID)
    _age_the_window(cosmos, PLAYER_ID, STORY_ID, ATTEMPT_WINDOW - datetime.timedelta(minutes=1))

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 2


def test_a_lapsed_window_reads_as_no_attempts():
    """FR-014's Edge Case: a player who reached the cap must have a next action that
    works. Without this the count only ever cleared on a successful session creation,
    which the cap itself made unreachable."""
    service, cosmos = _service_with_cosmos()
    for _ in range(5):
        service.record_attempt(PLAYER_ID, STORY_ID)
    _age_the_window(cosmos, PLAYER_ID, STORY_ID, ATTEMPT_WINDOW)

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 0


def test_a_lapsed_window_restarts_counting_at_one():
    service, cosmos = _service_with_cosmos()
    service.record_attempt(PLAYER_ID, STORY_ID)
    service.record_attempt(PLAYER_ID, STORY_ID)
    _age_the_window(cosmos, PLAYER_ID, STORY_ID, ATTEMPT_WINDOW + datetime.timedelta(minutes=5))

    assert service.record_attempt(PLAYER_ID, STORY_ID) == 1
    assert service.get_attempts(PLAYER_ID, STORY_ID) == 1


def test_a_document_written_before_windows_existed_reads_as_expired():
    """No migration: a pre-existing document carries no `windowStartedAt`, and anyone the
    old permanent counter had already stranded is released on their next attempt."""
    service, cosmos = _service_with_cosmos()
    cosmos.get_container(config.AVATAR_SETUP_ATTEMPTS_CONTAINER).create_item(
        {
            "id": f"{PLAYER_ID}:{STORY_ID}",
            "entityType": "AvatarSetupAttempts",
            "playerId": PLAYER_ID,
            "storyId": STORY_ID,
            "modelBackedAttempts": 5,
        }
    )

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 0


@pytest.mark.parametrize("bad_value", ["not-a-timestamp", 1789500000, {"seconds": 12}, []])
def test_an_unreadable_window_reads_as_expired(bad_value):
    """A malformed timestamp must never be the thing that keeps a player locked out — and
    a non-string value raises TypeError rather than ValueError, which would otherwise
    escape and 500 every start request for this pair."""
    service, cosmos = _service_with_cosmos()
    service.record_attempt(PLAYER_ID, STORY_ID)
    cosmos.get_container(config.AVATAR_SETUP_ATTEMPTS_CONTAINER).items[f"{PLAYER_ID}:{STORY_ID}"][
        "windowStartedAt"
    ] = bad_value

    assert service.get_attempts(PLAYER_ID, STORY_ID) == 0
