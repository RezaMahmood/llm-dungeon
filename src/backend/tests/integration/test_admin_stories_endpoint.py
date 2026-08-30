"""Integration tests for the story-creation draft/story endpoints (contracts/api.md,
FR-007). Cosmos is faked in-memory (matching this repo's other "integration" tests, which
mock Cosmos rather than requiring a live instance); TTL expiry (research.md §3) is
simulated by directly evicting the faked item, since a mocked container can't enforce a
real Cosmos TTL."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.admin.stories import (
    create_draft,
    get_draft,
    get_story,
    list_stories,
    patch_draft,
    post_message,
)
from backend.services.llm_service import LLMOutputError
from backend.services.story_draft_service import StoryDraftService
from backend.services.story_service import StoryService

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"
ADMIN_EMAIL = "admin@example.com"


class FakeContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def read_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        return self.items[item]

    def upsert_item(self, body):
        self.items[body["id"]] = body
        return body

    def delete_item(self, item, partition_key):  # noqa: ARG002
        self.items.pop(item, None)

    def expire(self, item_id: str) -> None:
        """Simulates Cosmos's native TTL eviction of an abandoned draft (research.md §3) —
        a mocked container can't enforce a real per-item TTL, so tests trigger the same
        end state (the item is simply gone) directly."""
        self.items.pop(item_id, None)


class FakeCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, FakeContainer] = {}

    def get_container(self, name: str) -> FakeContainer:
        return self._containers.setdefault(name, FakeContainer())

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        rows = list(self.get_container(container_name).items.values())
        if "entityType = 'Story'" in sql:
            rows = [r for r in rows if r.get("entityType") == "Story"]
        if sql.strip().upper().startswith("SELECT C.ID"):
            rows = [{"id": r["id"], "name": r.get("name"), "published": r.get("published"), "createdAt": r.get("createdAt")} for r in rows]
        return rows


def _services():
    cosmos = FakeCosmosService()
    llm = MagicMock()
    story_service = StoryService(cosmos_service=cosmos)
    draft_service = StoryDraftService(cosmos_service=cosmos, llm_service=llm, story_service=story_service)
    return draft_service, story_service, llm, cosmos


def _authorized(request_factory, method="GET", url="/api/manage/stories", body=b"", route_params=None):
    return request_factory(method=method, url=url, token="valid-token", body=body, route_params=route_params)


def _patched_authorize_admin():
    return patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None))


def _character_types():
    return [{"name": "Curious Cousin", "description": "Visiting for the summer."}]


def _completion_criteria():
    return {"maxDurationMinutes": None, "successConditions": ["Find the keeper"], "failureConditions": [], "rule": None}


# --- Eliciting setting/plot via POST .../messages ---


def test_message_elicits_setting_plot_and_merges_field_updates(request_factory):
    draft_service, _stories, llm, _cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(_authorized(request_factory, method="POST", url="/api/manage/stories/drafts"), story_draft_service=draft_service)
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    llm.generate_exchange_response.return_value = {
        "assistantMessage": "Who is the player, and what draws them there?",
        "fieldUpdates": {"worldPrompt": "A half-abandoned lighthouse on a cold northern cove."},
    }
    req = _authorized(
        request_factory,
        method="POST",
        url=f"/api/manage/stories/drafts/{draft_id}/messages",
        body=json.dumps({"message": "A half-abandoned lighthouse on a cold northern cove."}).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = post_message(req, story_draft_service=draft_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert body["draft"]["worldPrompt"] == "A half-abandoned lighthouse on a cold northern cove."
    assert body["draft"]["exchanges"][-1]["message"] == "Who is the player, and what draws them there?"
    assert body["readyToGenerate"] is False


# --- Eliciting character types and completion criteria via PATCH ---


def test_patch_elicits_character_types_and_completion_criteria(request_factory):
    draft_service, _stories, _llm, _cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(_authorized(request_factory, method="POST", url="/api/manage/stories/drafts"), story_draft_service=draft_service)
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    req = _authorized(
        request_factory,
        method="PATCH",
        url=f"/api/manage/stories/drafts/{draft_id}",
        body=json.dumps({"characterTypes": _character_types(), "completionCriteria": _completion_criteria()}).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = patch_draft(req, story_draft_service=draft_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["draft"]["characterTypes"] == _character_types()
    assert body["draft"]["completionCriteria"] == _completion_criteria()


# --- Automatic generation + persistence on completeness (SC-001, SC-003) ---


def test_completing_the_draft_generates_and_persists_a_story_automatically(request_factory):
    draft_service, story_service, llm, _cosmos = _services()
    llm.generate_exchange_response.return_value = {"assistantMessage": "Noted.", "fieldUpdates": {"worldPrompt": "A half-abandoned lighthouse."}}
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(
                request_factory,
                method="POST",
                url="/api/manage/stories/drafts",
                body=json.dumps({"idea": "A half-abandoned lighthouse on a cold northern cove."}).encode(),
            ),
            story_draft_service=draft_service,
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    llm.generate_story_config.return_value = {"narrativeGuidance": "Keep it eerie but never actually dangerous."}
    req = _authorized(
        request_factory,
        method="PATCH",
        url=f"/api/manage/stories/drafts/{draft_id}",
        body=json.dumps({"characterTypes": _character_types(), "completionCriteria": _completion_criteria()}).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = patch_draft(req, story_draft_service=draft_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "generated"
    story_id = body["storyId"]
    assert body["story"]["published"] is False
    assert body["story"]["characterTypes"] == _character_types()
    assert body["story"]["completionCriteria"]["successConditions"] == ["Find the keeper"]
    assert body["story"]["narrativeGuidance"] == "Keep it eerie but never actually dangerous."

    # The draft is gone, and the persisted story is independently fetchable.
    with _patched_authorize_admin():
        get_response = get_draft(
            _authorized(request_factory, url=f"/api/manage/stories/drafts/{draft_id}", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )
    assert get_response.status_code == 404

    with _patched_authorize_admin():
        story_response = get_story(
            _authorized(request_factory, url=f"/api/manage/stories/{story_id}", route_params={"storyId": story_id}),
            story_service=story_service,
        )
    assert story_response.status_code == 200


# --- Abandonment leaves nothing persisted once the draft's TTL expires (SC-002) ---


def test_abandoned_draft_is_gone_after_ttl_expiry_and_never_listed(request_factory):
    draft_service, story_service, _llm, cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    with _patched_authorize_admin():
        list_response = list_stories(_authorized(request_factory), story_service=story_service)
    assert json.loads(list_response.get_body())["stories"] == []

    cosmos.get_container("storyDrafts").expire(draft_id)

    with _patched_authorize_admin():
        get_response = get_draft(
            _authorized(request_factory, url=f"/api/manage/stories/drafts/{draft_id}", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )
    assert get_response.status_code == 404
    assert json.loads(get_response.get_body())["error"] == "not_found"


# --- A fresh session does not resume an abandoned one ---


def test_starting_a_new_draft_does_not_resume_an_earlier_unfinished_one(request_factory):
    draft_service, _stories, llm, _cosmos = _services()
    llm.generate_exchange_response.return_value = {"assistantMessage": "Tell me more.", "fieldUpdates": {"worldPrompt": "Idea one."}}
    with _patched_authorize_admin():
        first = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({"idea": "Idea one."}).encode()),
            story_draft_service=draft_service,
        )
    with _patched_authorize_admin():
        second = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )

    first_draft = json.loads(first.get_body())["draft"]
    second_draft = json.loads(second.get_body())["draft"]
    assert first_draft["id"] != second_draft["id"]
    assert second_draft["worldPrompt"] is None
    assert second_draft["exchanges"] == []


# --- 502 generation_failed leaves the draft intact ---


def test_malformed_generation_output_returns_502_and_leaves_draft_intact(request_factory):
    draft_service, _stories, llm, cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    llm.generate_story_config.side_effect = LLMOutputError("model returned malformed JSON")
    req = _authorized(
        request_factory,
        method="PATCH",
        url=f"/api/manage/stories/drafts/{draft_id}",
        body=json.dumps(
            {"worldPrompt": "A half-abandoned lighthouse.", "characterTypes": _character_types(), "completionCriteria": _completion_criteria()}
        ).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = patch_draft(req, story_draft_service=draft_service)

    assert response.status_code == 502
    assert json.loads(response.get_body())["error"] == "generation_failed"

    # The draft is left intact — GET still returns it, unchanged.
    assert cosmos.get_container("storyDrafts").items[draft_id]["worldPrompt"] == "A half-abandoned lighthouse."
    with _patched_authorize_admin():
        get_response = get_draft(
            _authorized(request_factory, url=f"/api/manage/stories/drafts/{draft_id}", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )
    assert get_response.status_code == 200
