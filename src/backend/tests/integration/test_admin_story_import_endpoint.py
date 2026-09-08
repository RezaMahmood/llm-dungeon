"""Integration tests for POST /api/manage/stories/import (contracts/api.md; quickstart.md
scenarios 8, 9, 10, 11, 16; SC-002)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.api.admin.stories import get_story_configuration, import_story
from backend.api.utils import forbidden_insufficient_permission, unauthorized
from backend.services.story_service import StoryService
from backend.tests.conftest import _make_starting_point, _make_story

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"


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

    def upsert_item(self, body):
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[body["id"]] = body
        return body

    def replace_item(self, item, body, etag=None, match_condition=None):
        current = self.items.get(item)
        if match_condition == MatchConditions.IfNotModified and current is not None and current.get("_etag") != etag:
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

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        return list(self.get_container(container_name).items.values())


def _valid_payload(**overrides):
    payload = {
        "name": "The Sunken Library",
        "worldPrompt": "A flooded library beneath a coastal town.",
        "characterTypes": [{"name": "Archivist", "description": "Knows where everything was."}],
        "completionCriteria": {"successConditions": ["Recover the tide ledger"]},
    }
    payload.update(overrides)
    return payload


def _services():
    cosmos = FakeCosmosService()
    llm = MagicMock()
    llm.generate_story_config.return_value = {"narrativeGuidance": "Refreshed guidance."}
    llm.generate_starting_point.return_value = _make_starting_point().to_dict()
    return StoryService(cosmos_service=cosmos, llm_service=llm), cosmos, llm


def _authorized(request_factory, body: dict):
    return request_factory(method="POST", url="/api/manage/stories/import", token="valid-token", body=json.dumps(body).encode())


def _patched_authorize_admin():
    return patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None))


def _seed_story(story_service, **overrides):
    story = _make_story(**overrides)
    story_service._container().upsert_item(story.to_dict())
    return story


def test_import_rejects_malformed_json(request_factory):
    story_service, _cosmos, _llm = _services()

    with _patched_authorize_admin():
        response = import_story(
            _authorized(request_factory, {"configurationText": "{ not valid"}), story_service=story_service
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "invalid_configuration"


def test_import_rejects_non_object_payload(request_factory):
    story_service, _cosmos, _llm = _services()

    with _patched_authorize_admin():
        response = import_story(
            _authorized(request_factory, {"configurationText": json.dumps(["not", "an", "object"])}),
            story_service=story_service,
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "invalid_configuration"


def test_import_overwrites_confirmed_id_matched_story(request_factory):
    story_service, _cosmos, _llm = _services()
    _seed_story(story_service, id="story-1", name="Old Name", contentVersion=1)
    payload = _valid_payload(id="story-1")

    with _patched_authorize_admin():
        response = import_story(
            _authorized(
                request_factory,
                {"configurationText": json.dumps(payload), "confirmOverwriteStoryId": "story-1"},
            ),
            story_service=story_service,
        )

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "updated"
    assert body["story"]["name"] == "The Sunken Library"
    assert body["story"]["contentVersion"] == 2


def test_import_requires_confirmation_for_id_matched_story(request_factory):
    story_service, _cosmos, _llm = _services()
    _seed_story(story_service, id="story-1", contentVersion=1)
    payload = _valid_payload(id="story-1")

    with _patched_authorize_admin():
        response = import_story(
            _authorized(request_factory, {"configurationText": json.dumps(payload)}), story_service=story_service
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "confirmation_required"
    assert story_service.get_story("story-1").contentVersion == 1


def test_import_creates_new_story_when_id_absent_with_title(request_factory):
    story_service, _cosmos, _llm = _services()
    payload = _valid_payload()

    with _patched_authorize_admin():
        response = import_story(
            _authorized(
                request_factory, {"configurationText": json.dumps(payload), "title": "A Brand New Tale"}
            ),
            story_service=story_service,
        )

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["status"] == "created"
    assert body["story"]["name"] == "A Brand New Tale"
    assert body["story"]["published"] is False


def test_import_requires_title_when_id_absent(request_factory):
    story_service, _cosmos, _llm = _services()
    payload = _valid_payload()

    with _patched_authorize_admin():
        response = import_story(
            _authorized(request_factory, {"configurationText": json.dumps(payload)}), story_service=story_service
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "title_required"


def test_import_rejects_unmatched_id_with_404_and_creates_nothing(request_factory):
    story_service, cosmos, _llm = _services()
    payload = _valid_payload(id="missing-id")

    with _patched_authorize_admin():
        response = import_story(
            _authorized(
                request_factory, {"configurationText": json.dumps(payload), "confirmOverwriteStoryId": "missing-id"}
            ),
            story_service=story_service,
        )

    assert response.status_code == 404
    assert json.loads(response.get_body())["error"] == "story_not_found"
    assert cosmos.get_container("stories").items == {}


def test_import_rejects_invalid_configuration_content_reasons(request_factory):
    story_service, _cosmos, _llm = _services()
    payload = _valid_payload()
    del payload["completionCriteria"]

    with _patched_authorize_admin():
        response = import_story(
            _authorized(request_factory, {"configurationText": json.dumps(payload), "title": "x"}),
            story_service=story_service,
        )

    assert response.status_code == 422
    assert "completionCriteria" in json.loads(response.get_body())["message"]


def test_download_reupload_download_round_trip_is_byte_identical(request_factory):
    story_service, _cosmos, _llm = _services()
    _seed_story(story_service, id="story-1", name="The Sunken Library", contentVersion=1)

    with _patched_authorize_admin():
        first_download = get_story_configuration(
            request_factory(method="GET", url="/api/manage/stories/story-1/configuration", token="valid-token", route_params={"storyId": "story-1"}),
            story_service=story_service,
        )
    downloaded_text = first_download.get_body().decode("utf-8")

    with _patched_authorize_admin():
        import_response = import_story(
            _authorized(
                request_factory, {"configurationText": downloaded_text, "confirmOverwriteStoryId": "story-1"}
            ),
            story_service=story_service,
        )
    assert import_response.status_code == 200

    with _patched_authorize_admin():
        second_download = get_story_configuration(
            request_factory(method="GET", url="/api/manage/stories/story-1/configuration", token="valid-token", route_params={"storyId": "story-1"}),
            story_service=story_service,
        )

    assert second_download.get_body().decode("utf-8") == downloaded_text


def test_import_persists_an_edited_guidance_and_starting_point(request_factory):
    """#270, #271: both are authored content in the file, so an admin's edits survive the
    upload instead of being regenerated over."""
    story_service, _cosmos, llm = _services()
    _seed_story(story_service, id="story-1", name="Old Name", contentVersion=1)
    payload = _valid_payload(
        id="story-1",
        narrativeGuidance="Hand-edited guidance.",
        startingPoint={
            "narrativeText": "Hand-edited opening.",
            "suggestedActions": ["Wade in", "Call out"],
            "locationLabel": "Library steps",
            "goalLabel": None,
            "progress": None,
        },
    )

    with _patched_authorize_admin():
        response = import_story(
            _authorized(
                request_factory,
                {"configurationText": json.dumps(payload), "confirmOverwriteStoryId": "story-1"},
            ),
            story_service=story_service,
        )

    assert response.status_code == 200
    stored = story_service.get_story("story-1")
    assert stored.narrativeGuidance == "Hand-edited guidance."
    assert stored.startingPoint.narrativeText == "Hand-edited opening."
    llm.generate_story_config.assert_not_called()
    llm.generate_starting_point.assert_not_called()


def test_import_regenerates_guidance_and_starting_point_when_the_file_omits_them(request_factory):
    story_service, _cosmos, llm = _services()
    _seed_story(story_service, id="story-1", name="Old Name", contentVersion=1)

    with _patched_authorize_admin():
        response = import_story(
            _authorized(
                request_factory,
                {"configurationText": json.dumps(_valid_payload(id="story-1")), "confirmOverwriteStoryId": "story-1"},
            ),
            story_service=story_service,
        )

    assert response.status_code == 200
    stored = story_service.get_story("story-1")
    assert stored.narrativeGuidance == "Refreshed guidance."
    assert stored.startingPoint == _make_starting_point()


def test_import_returns_write_conflict_after_repeated_etag_precondition_failure(request_factory):
    story_service, cosmos, _llm = _services()
    _seed_story(story_service, id="story-1", contentVersion=1)
    container = cosmos.get_container("stories")
    container.replace_item = MagicMock(side_effect=CosmosAccessConditionFailedError)
    payload = _valid_payload(id="story-1")

    with _patched_authorize_admin():
        response = import_story(
            _authorized(
                request_factory, {"configurationText": json.dumps(payload), "confirmOverwriteStoryId": "story-1"}
            ),
            story_service=story_service,
        )

    assert response.status_code == 409
    assert json.loads(response.get_body())["error"] == "write_conflict"


def test_import_requires_authentication(request_factory):
    story_service, _cosmos, _llm = _services()
    with patch("backend.api.admin.stories.authorize_admin", return_value=(False, None, unauthorized())):
        response = import_story(_authorized(request_factory, {"configurationText": "{}"}), story_service=story_service)
    assert response.status_code == 401


def test_import_requires_administrator_role(request_factory):
    story_service, _cosmos, _llm = _services()
    with patch(
        "backend.api.admin.stories.authorize_admin",
        return_value=(False, ADMIN_OID, forbidden_insufficient_permission()),
    ):
        response = import_story(_authorized(request_factory, {"configurationText": "{}"}), story_service=story_service)
    assert response.status_code == 403
