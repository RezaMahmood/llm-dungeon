"""Integration tests for the wizard-edit endpoints (contracts/api.md → POST …/edit-drafts,
POST …/drafts/{draftId}/save; quickstart.md scenarios 5, 6, 7, 16; SC-003, SC-004)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError

from backend.api.admin.stories import create_edit_draft, generate_story_from_draft, save_draft
from backend.api.utils import forbidden_insufficient_permission, unauthorized
from backend.services.story_draft_service import StoryDraftService
from backend.services.story_service import StoryService
from backend.tests.conftest import _make_starting_point

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

    def delete_item(self, item, partition_key):  # noqa: ARG002
        self.items.pop(item, None)


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        return list(self.get_container(container_name).items.values())


def _services():
    cosmos = FakeCosmosService()
    llm = MagicMock()
    llm.generate_story_config.return_value = {"narrativeGuidance": "Refreshed guidance."}
    llm.generate_starting_point.return_value = _make_starting_point().to_dict()
    story_service = StoryService(cosmos_service=cosmos, llm_service=llm)
    draft_service = StoryDraftService(cosmos_service=cosmos, llm_service=llm, story_service=story_service)
    return story_service, draft_service, llm, cosmos


def _authorized(request_factory, method="GET", url="/api/x", body=b"", route_params=None):
    return request_factory(method=method, url=url, token="valid-token", body=body, route_params=route_params)


def _patched_authorize_admin():
    return patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None))


def _seed_story(story_service, **overrides):
    from backend.tests.conftest import _make_story

    story = _make_story(**overrides)
    story_service._container().upsert_item(story.to_dict())
    return story


def test_create_edit_draft_returns_201_seeded_from_story(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    story = _seed_story(story_service, id="story-1", name="The Sunken Library", contentVersion=4)

    with _patched_authorize_admin():
        response = create_edit_draft(
            _authorized(
                request_factory, method="POST", url="/api/manage/stories/story-1/edit-drafts", route_params={"storyId": "story-1"}
            ),
            story_service=story_service,
            story_draft_service=draft_service,
        )

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["draft"]["sourceStoryId"] == "story-1"
    assert body["draft"]["baseContentVersion"] == 4
    assert body["draft"]["name"] == "The Sunken Library"


def test_create_edit_draft_returns_404_for_missing_story(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()

    with _patched_authorize_admin():
        response = create_edit_draft(
            _authorized(
                request_factory, method="POST", url="/api/manage/stories/missing/edit-drafts", route_params={"storyId": "missing"}
            ),
            story_service=story_service,
            story_draft_service=draft_service,
        )

    assert response.status_code == 404


def test_create_edit_draft_never_blocked_by_publish_state(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    _seed_story(
        story_service,
        id="story-1",
        published=True,
        contentUpdatedAt="2026-08-30T09:00:00Z",
        lastTestPlayedAt="2026-08-30T09:00:00Z",
    )

    with _patched_authorize_admin():
        response = create_edit_draft(
            _authorized(
                request_factory, method="POST", url="/api/manage/stories/story-1/edit-drafts", route_params={"storyId": "story-1"}
            ),
            story_service=story_service,
            story_draft_service=draft_service,
        )

    assert response.status_code == 201


def _open_edit_draft(request_factory, story_service, draft_service, story_id="story-1"):
    with _patched_authorize_admin():
        response = create_edit_draft(
            _authorized(
                request_factory, method="POST", url=f"/api/manage/stories/{story_id}/edit-drafts", route_params={"storyId": story_id}
            ),
            story_service=story_service,
            story_draft_service=draft_service,
        )
    return json.loads(response.get_body())["draft"]["id"]


def test_save_draft_returns_200_and_updates_story_preserving_untouched_fields(request_factory):
    story_service, draft_service, llm, _cosmos = _services()
    story = _seed_story(
        story_service,
        id="story-1",
        name="The Sunken Library",
        createdBy="creator-oid",
        createdAt="2026-08-01T00:00:00Z",
        published=True,
        lastPublishedAt="2026-08-20T00:00:00Z",
        contentVersion=1,
    )
    draft_id = _open_edit_draft(request_factory, story_service, draft_service)

    with _patched_authorize_admin():
        response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/save", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "saved"
    saved_story = body["story"]
    assert saved_story["id"] == story.id
    assert saved_story["createdBy"] == "creator-oid"
    assert saved_story["createdAt"] == "2026-08-01T00:00:00Z"
    assert saved_story["published"] is True
    assert saved_story["lastPublishedAt"] == "2026-08-20T00:00:00Z"
    assert saved_story["contentVersion"] == 2
    assert saved_story["lastUpdatedBy"] == ADMIN_OID
    assert saved_story["name"] == "The Sunken Library"


def test_save_draft_rejects_stale_save_and_leaves_first_saves_state_intact(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    _seed_story(story_service, id="story-1", name="The Sunken Library", contentVersion=1)
    first_draft_id = _open_edit_draft(request_factory, story_service, draft_service)
    second_draft_id = _open_edit_draft(request_factory, story_service, draft_service)

    with _patched_authorize_admin():
        first_response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{first_draft_id}/save", route_params={"draftId": first_draft_id}),
            story_draft_service=draft_service,
        )
    assert first_response.status_code == 200
    first_story = json.loads(first_response.get_body())["story"]

    with _patched_authorize_admin():
        second_response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{second_draft_id}/save", route_params={"draftId": second_draft_id}),
            story_draft_service=draft_service,
        )

    assert second_response.status_code == 409
    assert json.loads(second_response.get_body())["error"] == "stale_story"

    # First save's state is intact.
    current = story_service.get_story("story-1")
    assert current.contentVersion == first_story["contentVersion"]

    # And the rejected (second) draft survives — GET must still work for it.
    assert draft_service.get_draft(second_draft_id) is not None


def test_save_draft_returns_422_not_ready_when_a_required_element_is_cleared(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    _seed_story(story_service, id="story-1", name="The Sunken Library")
    draft_id = _open_edit_draft(request_factory, story_service, draft_service)
    draft = draft_service.get_draft(draft_id)
    draft.worldPrompt = None
    story_service._cosmos.get_container("storyDrafts").upsert_item(draft.to_dict())

    with _patched_authorize_admin():
        response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/save", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "not_ready"
    assert story_service.get_story("story-1").worldPrompt is not None


def test_save_draft_returns_422_wrong_draft_mode_for_a_creation_draft(request_factory):
    from backend.api.admin.stories import create_draft

    story_service, draft_service, _llm, _cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts"), story_draft_service=draft_service
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    with _patched_authorize_admin():
        response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/save", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "wrong_draft_mode"


def test_generate_rejects_an_edit_draft_with_422_wrong_draft_mode(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    _seed_story(story_service, id="story-1", name="The Sunken Library")
    draft_id = _open_edit_draft(request_factory, story_service, draft_service)

    with _patched_authorize_admin():
        response = generate_story_from_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/generate", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "wrong_draft_mode"


def test_save_draft_returns_404_for_missing_draft(request_factory):
    _story_service, draft_service, _llm, _cosmos = _services()

    with _patched_authorize_admin():
        response = save_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts/missing/save", route_params={"draftId": "missing"}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 404


def test_save_draft_returns_write_conflict_after_repeated_etag_precondition_failure(request_factory):
    story_service, draft_service, _llm, cosmos = _services()
    _seed_story(story_service, id="story-1", name="The Sunken Library")
    draft_id = _open_edit_draft(request_factory, story_service, draft_service)

    container = cosmos.get_container("stories")
    container.replace_item = MagicMock(side_effect=CosmosAccessConditionFailedError)

    with _patched_authorize_admin():
        response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/save", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 409
    assert json.loads(response.get_body())["error"] == "write_conflict"


def test_save_draft_survives_a_publish_landing_between_seed_and_save(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    _seed_story(
        story_service,
        id="story-1",
        name="The Sunken Library",
        contentUpdatedAt="2026-08-30T09:00:00Z",
        lastTestPlayedAt="2026-08-30T09:00:00Z",
    )
    draft_id = _open_edit_draft(request_factory, story_service, draft_service)

    # A publish lands between the draft's seeding and its save — contentVersion is
    # untouched by publish, so this must not read as staleness.
    published = story_service.publish("story-1")
    assert published.published is True

    with _patched_authorize_admin():
        response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/save", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )

    assert response.status_code == 200
    saved_story = json.loads(response.get_body())["story"]
    assert saved_story["published"] is True


def test_create_edit_draft_requires_authentication(request_factory):
    story_service, draft_service, _llm, _cosmos = _services()
    with patch("backend.api.admin.stories.authorize_admin", return_value=(False, None, unauthorized())):
        response = create_edit_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/story-1/edit-drafts", route_params={"storyId": "story-1"}),
            story_service=story_service,
            story_draft_service=draft_service,
        )
    assert response.status_code == 401


def test_save_draft_requires_administrator_role(request_factory):
    _story_service, draft_service, _llm, _cosmos = _services()
    with patch(
        "backend.api.admin.stories.authorize_admin",
        return_value=(False, ADMIN_OID, forbidden_insufficient_permission()),
    ):
        response = save_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts/draft-1/save", route_params={"draftId": "draft-1"}),
            story_draft_service=draft_service,
        )
    assert response.status_code == 403
