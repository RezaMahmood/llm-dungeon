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
    create_edit_draft,
    generate_story_from_draft,
    get_draft,
    get_story,
    list_stories,
    patch_draft,
    save_draft,
    suggest_world_prompt,
)
from backend.services.llm_service import LLMOutputError, LLMRateLimitError
from backend.services.story_draft_service import StoryDraftService
from backend.services.story_service import StoryService
from backend.services.test_play_session_service import TestPlaySessionService
from backend.tests.conftest import _make_starting_point

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"
ADMIN_EMAIL = "admin@example.com"


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

    def upsert_item(self, body):
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[body["id"]] = body
        return body

    def replace_item(self, item, body, etag=None, match_condition=None):
        from azure.core import MatchConditions
        from azure.cosmos.exceptions import CosmosAccessConditionFailedError

        current = self.items.get(item)
        if match_condition == MatchConditions.IfNotModified and current is not None and current.get("_etag") != etag:
            raise CosmosAccessConditionFailedError
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[item] = body
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
            rows = [
                {
                    "id": r["id"],
                    "name": r.get("name"),
                    "published": r.get("published"),
                    "createdAt": r.get("createdAt"),
                    "totalTokens": r.get("totalTokens"),
                }
                for r in rows
            ]
        return rows


def _services():
    cosmos = FakeCosmosService()
    llm = MagicMock()
    story_service = StoryService(cosmos_service=cosmos, llm_service=llm)
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


# --- Turning an idea into a world prompt via POST .../world-prompt ---


def test_idea_is_turned_into_a_world_prompt_in_one_pass(request_factory):
    """#227 — the idea goes to the model exactly once, the suggestion lands in
    worldPrompt, and no conversation history comes back with it."""
    draft_service, _stories, llm, _cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(_authorized(request_factory, method="POST", url="/api/manage/stories/drafts"), story_draft_service=draft_service)
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse on a cold northern cove.", 12)
    req = _authorized(
        request_factory,
        method="POST",
        url=f"/api/manage/stories/drafts/{draft_id}/world-prompt",
        body=json.dumps({"idea": "A lighthouse nobody has visited in years."}).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = suggest_world_prompt(req, story_draft_service=draft_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert body["draft"]["worldPrompt"] == "A half-abandoned lighthouse on a cold northern cove."
    assert "exchanges" not in body["draft"]
    llm.suggest_world_prompt.assert_called_once()
    assert body["readyToGenerate"] is False


def test_world_prompt_suggestion_rejects_a_blank_idea(request_factory):
    draft_service, _stories, llm, _cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(_authorized(request_factory, method="POST", url="/api/manage/stories/drafts"), story_draft_service=draft_service)
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    req = _authorized(
        request_factory,
        method="POST",
        url=f"/api/manage/stories/drafts/{draft_id}/world-prompt",
        body=json.dumps({}).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = suggest_world_prompt(req, story_draft_service=draft_service)

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "invalid_field"
    llm.suggest_world_prompt.assert_not_called()


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


# --- Completing a draft never auto-generates or auto-navigates (#33) ---


def test_completing_the_draft_via_patch_does_not_generate_or_redirect(request_factory):
    """Filling in the last required field (e.g. blurring a completion-criteria box) must
    only report readyToGenerate — it must never itself produce a "generated" response,
    since that's what previously caused the wizard to redirect away without the
    administrator explicitly finishing (#33)."""
    draft_service, _stories, llm, _cosmos = _services()
    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse.", 12)
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

    req = _authorized(
        request_factory,
        method="PATCH",
        url=f"/api/manage/stories/drafts/{draft_id}",
        body=json.dumps(
            {"name": "The Lighthouse at Gullwing Cove", "characterTypes": _character_types(), "completionCriteria": _completion_criteria()}
        ).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = patch_draft(req, story_draft_service=draft_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert body["readyToGenerate"] is True
    llm.generate_story_config.assert_not_called()

    # Still resumable — the draft was persisted, not deleted/converted into a story.
    with _patched_authorize_admin():
        get_response = get_draft(
            _authorized(request_factory, url=f"/api/manage/stories/drafts/{draft_id}", route_params={"draftId": draft_id}),
            story_draft_service=draft_service,
        )
    assert get_response.status_code == 200


# --- Explicit "generate" action (#33) ---


def test_generate_action_persists_a_story_only_when_explicitly_called(request_factory):
    draft_service, story_service, llm, _cosmos = _services()
    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse.", 12)
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

    with _patched_authorize_admin():
        patch_draft(
            _authorized(
                request_factory,
                method="PATCH",
                url=f"/api/manage/stories/drafts/{draft_id}",
                body=json.dumps(
                    {
                        "name": "The Lighthouse at Gullwing Cove",
                        "characterTypes": _character_types(),
                        "completionCriteria": _completion_criteria(),
                    }
                ).encode(),
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

    llm.generate_story_config.return_value = ({"narrativeGuidance": "Keep it eerie but never actually dangerous."}, 30)
    llm.generate_starting_point.return_value = (_make_starting_point().to_dict(), 40)
    with _patched_authorize_admin():
        response = generate_story_from_draft(
            _authorized(
                request_factory,
                method="POST",
                url=f"/api/manage/stories/drafts/{draft_id}/generate",
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

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
    # 012-story-editing-and-review T015: contentVersion/lastUpdatedBy are exposed for
    # visibility and tests only — the FR-006 staleness check runs server-side, so a fresh
    # story reads contentVersion 1 and no lastUpdatedBy yet.
    story_body = json.loads(story_response.get_body())["story"]
    assert story_body["contentVersion"] == 1
    assert story_body["lastUpdatedBy"] is None


def test_generated_story_reports_its_total_tokens_in_the_stories_list(request_factory):
    """contracts/api.md → GET /api/manage/stories: totalTokens reflects the world-prompt
    suggestion plus the generation and starting-point calls (quickstart.md Scenario 1)."""
    draft_service, story_service, llm, _cosmos = _services()
    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse.", 12)
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

    with _patched_authorize_admin():
        patch_draft(
            _authorized(
                request_factory,
                method="PATCH",
                url=f"/api/manage/stories/drafts/{draft_id}",
                body=json.dumps(
                    {
                        "name": "The Lighthouse at Gullwing Cove",
                        "characterTypes": _character_types(),
                        "completionCriteria": _completion_criteria(),
                    }
                ).encode(),
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

    llm.generate_story_config.return_value = ({"narrativeGuidance": "Keep it eerie but safe."}, 30)
    llm.generate_starting_point.return_value = (_make_starting_point().to_dict(), 40)
    with _patched_authorize_admin():
        generate_story_from_draft(
            _authorized(
                request_factory,
                method="POST",
                url=f"/api/manage/stories/drafts/{draft_id}/generate",
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

    with _patched_authorize_admin():
        list_response = list_stories(_authorized(request_factory), story_service=story_service)

    [story] = json.loads(list_response.get_body())["stories"]
    assert story["totalTokens"] == 12 + 30 + 40


def test_stories_list_defaults_total_tokens_to_zero_for_a_legacy_row(request_factory):
    draft_service, story_service, _llm, cosmos = _services()
    with _patched_authorize_admin():
        create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )
    # Simulate a story persisted before totalTokens existed: no key on the stored row.
    cosmos.get_container("stories").items["legacy-story"] = {
        "id": "legacy-story",
        "entityType": "Story",
        "name": "A Legacy Tale",
        "published": False,
        "createdAt": "2026-01-01T00:00:00Z",
    }

    with _patched_authorize_admin():
        list_response = list_stories(_authorized(request_factory), story_service=story_service)

    [story] = json.loads(list_response.get_body())["stories"]
    assert story["totalTokens"] == 0


def test_generate_action_rejects_incomplete_draft(request_factory):
    draft_service, _stories, _llm, _cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    with _patched_authorize_admin():
        response = generate_story_from_draft(
            _authorized(
                request_factory,
                method="POST",
                url=f"/api/manage/stories/drafts/{draft_id}/generate",
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "not_ready"


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
    llm.suggest_world_prompt.return_value = ("Idea one.", 12)
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
    assert first_draft["worldPrompt"] == "Idea one."
    assert second_draft["worldPrompt"] is None


# --- 502 generation_failed leaves the draft intact ---


def test_malformed_generation_output_returns_502_and_leaves_draft_intact(request_factory):
    draft_service, _stories, llm, cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    with _patched_authorize_admin():
        patch_draft(
            _authorized(
                request_factory,
                method="PATCH",
                url=f"/api/manage/stories/drafts/{draft_id}",
                body=json.dumps(
                    {
                        "name": "The Lighthouse at Gullwing Cove",
                        "worldPrompt": "A half-abandoned lighthouse.",
                        "characterTypes": _character_types(),
                        "completionCriteria": _completion_criteria(),
                    }
                ).encode(),
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

    llm.generate_story_config.side_effect = LLMOutputError("model returned malformed JSON")
    with _patched_authorize_admin():
        response = generate_story_from_draft(
            _authorized(
                request_factory,
                method="POST",
                url=f"/api/manage/stories/drafts/{draft_id}/generate",
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )

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


# --- 429 rate_limited leaves the draft intact (#33) ---


def test_rate_limited_world_prompt_suggestion_returns_429_and_leaves_draft_intact(request_factory):
    draft_service, _stories, llm, cosmos = _services()
    with _patched_authorize_admin():
        create_response = create_draft(
            _authorized(request_factory, method="POST", url="/api/manage/stories/drafts", body=json.dumps({}).encode()),
            story_draft_service=draft_service,
        )
    draft_id = json.loads(create_response.get_body())["draft"]["id"]

    llm.suggest_world_prompt.side_effect = LLMRateLimitError("rate limited")
    req = _authorized(
        request_factory,
        method="POST",
        url=f"/api/manage/stories/drafts/{draft_id}/world-prompt",
        body=json.dumps({"idea": "A half-abandoned lighthouse."}).encode(),
        route_params={"draftId": draft_id},
    )
    with _patched_authorize_admin():
        response = suggest_world_prompt(req, story_draft_service=draft_service)

    assert response.status_code == 429
    assert json.loads(response.get_body())["error"] == "rate_limited"

    # Nothing from the failed suggestion was persisted.
    assert cosmos.get_container("storyDrafts").items[draft_id]["worldPrompt"] is None


# --- Token totals stay accurate across edit + test-play (026-token-usage, T047) ---


def test_editing_and_test_playing_a_story_increases_its_total_tokens(request_factory):
    """quickstart.md Scenario 2 / SC-003: a story's token total keeps growing across an
    edit-triggered regeneration and an admin test-play, on top of its creation total."""
    draft_service, story_service, llm, cosmos = _services()
    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse.", 12)
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
    with _patched_authorize_admin():
        patch_draft(
            _authorized(
                request_factory,
                method="PATCH",
                url=f"/api/manage/stories/drafts/{draft_id}",
                body=json.dumps(
                    {"name": "The Lighthouse at Gullwing Cove", "characterTypes": _character_types(), "completionCriteria": _completion_criteria()}
                ).encode(),
                route_params={"draftId": draft_id},
            ),
            story_draft_service=draft_service,
        )
    llm.generate_story_config.return_value = ({"narrativeGuidance": "Keep it eerie but safe."}, 30)
    llm.generate_starting_point.return_value = (_make_starting_point().to_dict(), 40)
    with _patched_authorize_admin():
        generate_response = generate_story_from_draft(
            _authorized(
                request_factory, method="POST", url=f"/api/manage/stories/drafts/{draft_id}/generate", route_params={"draftId": draft_id}
            ),
            story_draft_service=draft_service,
        )
    story_id = json.loads(generate_response.get_body())["storyId"]
    creation_total = 12 + 30 + 40

    with _patched_authorize_admin():
        list_response = list_stories(_authorized(request_factory), story_service=story_service)
    [story_row] = json.loads(list_response.get_body())["stories"]
    assert story_row["totalTokens"] == creation_total

    # Edit: reopen the story and save it in a way that triggers regeneration (no
    # narrativeGuidance/startingPoint supplied, so both are regenerated).
    with _patched_authorize_admin():
        edit_response = create_edit_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/{story_id}/edit-drafts", route_params={"storyId": story_id}),
            story_service=story_service,
            story_draft_service=draft_service,
        )
    edit_draft_id = json.loads(edit_response.get_body())["draft"]["id"]
    llm.generate_story_config.return_value = ({"narrativeGuidance": "Even eerier now."}, 20)
    llm.generate_starting_point.return_value = (_make_starting_point(narrativeText="A revised opening.").to_dict(), 25)
    with _patched_authorize_admin():
        save_response = save_draft(
            _authorized(request_factory, method="POST", url=f"/api/manage/stories/drafts/{edit_draft_id}/save", route_params={"draftId": edit_draft_id}),
            story_draft_service=draft_service,
        )
    assert save_response.status_code == 200
    after_edit_total = creation_total + 20 + 25
    assert story_service.get_story(story_id).totalTokens == after_edit_total

    # Test-play: a couple of exchanges, each adding to both the test session's own total
    # and the story's total (research.md Decision 3).
    test_play_service = TestPlaySessionService(cosmos_service=cosmos, story_service=story_service, llm_service=llm)
    llm.generate_gameplay_turn.return_value = (
        {
            "narrativeText": "You look around.",
            "suggestedActions": ["look", "wait"],
            "locationLabel": "The cove",
            "goalLabel": None,
            "progress": None,
            "newlySatisfiedSuccessConditions": [],
            "newlySatisfiedFailureConditions": [],
        },
        50,
    )
    session = test_play_service.create_session(story_id, ADMIN_OID)
    cosmos.get_container("testPlaySessions").items[session.id]["lastInteractionAt"] = "2020-01-01T00:00:00Z"
    test_play_service.submit_exchange(session.id, ADMIN_OID, "look around")
    cosmos.get_container("testPlaySessions").items[session.id]["lastInteractionAt"] = "2020-01-01T00:00:00Z"
    test_play_service.submit_exchange(session.id, ADMIN_OID, "look again")

    with _patched_authorize_admin():
        reload_response = list_stories(_authorized(request_factory), story_service=story_service)
    [reloaded_row] = json.loads(reload_response.get_body())["stories"]
    assert reloaded_row["totalTokens"] == after_edit_total + 50 + 50
