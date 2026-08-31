"""Integration tests for the story create/update/delete/cover-image/suggest-outline
endpoints (Session 2026-08-30 redesign, FR-007). Cosmos is faked in-memory (matching this
repo's other "integration" tests, which mock Cosmos rather than requiring a live
instance)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.api.admin.stories import (
    create_story,
    delete_story,
    get_story,
    list_stories,
    suggest_outline,
    update_story,
    upload_cover_image,
)
from backend.services.llm_service import LLMOutputError
from backend.services.story_service import StoryService

ADMIN_OID = "550e8400-e29b-41d4-a716-446655440000"
ADMIN_EMAIL = "admin@example.com"
OTHER_ADMIN_EMAIL = "editor@example.com"


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
        if item not in self.items:
            raise CosmosResourceNotFoundError
        self.items.pop(item, None)


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
    blob = MagicMock()
    blob.upload_cover_image.return_value = "https://example.blob.core.windows.net/assets/story-covers/story-1/cover.png"
    story_service = StoryService(cosmos_service=cosmos, blob_service=blob)
    return story_service, blob, cosmos


def _patched_auth(email: str = ADMIN_EMAIL):
    return (
        patch("backend.api.admin.stories.authorize_admin", return_value=(True, ADMIN_OID, None)),
        patch("backend.api.admin.stories.authenticate_with_email", return_value=(True, ADMIN_OID, email, None)),
    )


def _character_types():
    return [{"name": "Curious Cousin", "description": "Visiting for the summer."}]


def _completion_criteria():
    return {"maxDurationMinutes": None, "successConditions": ["Find the keeper"], "failureConditions": [], "rule": None}


# --- Save (create) creates a Story record with audit fields (FR-004, FR-012) ---


def test_create_story_persists_with_only_a_name_and_audit_fields(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()

    req = request_factory(method="POST", url="/api/manage/stories", token="valid-token", body=json.dumps({"name": "A New Story"}).encode())
    with auth_patch, email_patch:
        response = create_story(req, story_service=story_service)

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["status"] == "success"
    assert body["story"]["name"] == "A New Story"
    assert body["story"]["published"] is False
    assert body["story"]["createdBy"] == ADMIN_EMAIL
    assert body["story"]["updatedBy"] == ADMIN_EMAIL


def test_create_story_without_a_name_is_rejected(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()

    req = request_factory(method="POST", url="/api/manage/stories", token="valid-token", body=json.dumps({}).encode())
    with auth_patch, email_patch:
        response = create_story(req, story_service=story_service)

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"] == "invalid_field"


# --- Save (update) updates the existing record in place (FR-004) ---


def test_update_story_by_a_different_admin_stamps_the_new_updated_by(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()
    with auth_patch, email_patch:
        create_response = create_story(
            request_factory(method="POST", url="/api/manage/stories", token="valid-token", body=json.dumps({"name": "A Title"}).encode()),
            story_service=story_service,
        )
    story_id = json.loads(create_response.get_body())["story"]["id"]

    req = request_factory(
        method="PATCH",
        url=f"/api/manage/stories/{story_id}",
        token="valid-token",
        body=json.dumps({"outline": "Updated outline", "characterTypes": _character_types(), "completionCriteria": _completion_criteria()}).encode(),
        route_params={"storyId": story_id},
    )
    auth_patch2, email_patch2 = _patched_auth(OTHER_ADMIN_EMAIL)
    with auth_patch2, email_patch2:
        response = update_story(req, story_service=story_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())["story"]
    assert body["outline"] == "Updated outline"
    assert body["characterTypes"] == _character_types()
    assert body["updatedBy"] == OTHER_ADMIN_EMAIL
    assert body["createdBy"] == ADMIN_EMAIL


def test_update_story_returns_404_when_never_saved(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()

    req = request_factory(
        method="PATCH", url="/api/manage/stories/missing", token="valid-token", body=json.dumps({"outline": "x"}).encode(), route_params={"storyId": "missing"}
    )
    with auth_patch, email_patch:
        response = update_story(req, story_service=story_service)

    assert response.status_code == 404


# --- Abandon deletes the persisted record, or no-ops if never saved (FR-013/014) ---


def test_abandon_deletes_a_previously_saved_story(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()
    with auth_patch, email_patch:
        create_response = create_story(
            request_factory(method="POST", url="/api/manage/stories", token="valid-token", body=json.dumps({"name": "A Title"}).encode()),
            story_service=story_service,
        )
    story_id = json.loads(create_response.get_body())["story"]["id"]

    req = request_factory(method="DELETE", url=f"/api/manage/stories/{story_id}", token="valid-token", route_params={"storyId": story_id})
    with auth_patch, email_patch:
        response = delete_story(req, story_service=story_service)
    assert response.status_code == 200

    with auth_patch, email_patch:
        get_response = get_story(
            request_factory(method="GET", url=f"/api/manage/stories/{story_id}", token="valid-token", route_params={"storyId": story_id}),
            story_service=story_service,
        )
    assert get_response.status_code == 404


def test_abandon_is_a_no_op_when_the_story_was_never_saved(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()

    req = request_factory(method="DELETE", url="/api/manage/stories/never-saved", token="valid-token", route_params={"storyId": "never-saved"})
    with auth_patch, email_patch:
        response = delete_story(req, story_service=story_service)

    assert response.status_code == 200
    assert json.loads(response.get_body())["status"] == "success"


# --- Cover image upload (FR-009) ---


def test_upload_cover_image_stores_blob_reference_on_the_story(request_factory):
    story_service, blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()
    with auth_patch, email_patch:
        create_response = create_story(
            request_factory(method="POST", url="/api/manage/stories", token="valid-token", body=json.dumps({"name": "A Title"}).encode()),
            story_service=story_service,
        )
    story_id = json.loads(create_response.get_body())["story"]["id"]

    req = request_factory(
        method="POST",
        url=f"/api/manage/stories/{story_id}/cover-image",
        token="valid-token",
        body=b"fake-image-bytes",
        route_params={"storyId": story_id},
        headers={"Content-Type": "image/png", "X-File-Name": "cover.png"},
    )
    with auth_patch, email_patch:
        response = upload_cover_image(req, story_service=story_service)

    assert response.status_code == 200
    body = json.loads(response.get_body())["story"]
    assert body["coverImageUrl"] == "https://example.blob.core.windows.net/assets/story-covers/story-1/cover.png"
    blob.upload_cover_image.assert_called_once_with(story_id, "cover.png", b"fake-image-bytes", "image/png")


def test_upload_cover_image_returns_404_for_a_story_that_was_never_saved(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()

    req = request_factory(
        method="POST",
        url="/api/manage/stories/missing/cover-image",
        token="valid-token",
        body=b"fake-image-bytes",
        route_params={"storyId": "missing"},
        headers={"Content-Type": "image/png"},
    )
    with auth_patch, email_patch:
        response = upload_cover_image(req, story_service=story_service)

    assert response.status_code == 404


# --- Tab 02 one-shot outline suggestion (FR-003) ---


def test_suggest_outline_returns_a_generated_outline(request_factory):
    llm = MagicMock()
    llm.suggest_outline.return_value = "A half-abandoned lighthouse on a cold northern cove."
    auth_patch, email_patch = _patched_auth()

    req = request_factory(method="POST", url="/api/manage/stories/suggest-outline", token="valid-token", body=json.dumps({"idea": "a lighthouse mystery"}).encode())
    with auth_patch, email_patch:
        response = suggest_outline(req, llm_service=llm)

    assert response.status_code == 200
    body = json.loads(response.get_body())
    assert body["outline"] == "A half-abandoned lighthouse on a cold northern cove."
    llm.suggest_outline.assert_called_once_with("a lighthouse mystery")


def test_suggest_outline_surfaces_generation_failure_without_touching_anything(request_factory):
    llm = MagicMock()
    llm.suggest_outline.side_effect = LLMOutputError("model returned malformed JSON")
    auth_patch, email_patch = _patched_auth()

    req = request_factory(method="POST", url="/api/manage/stories/suggest-outline", token="valid-token", body=json.dumps({"idea": "a lighthouse mystery"}).encode())
    with auth_patch, email_patch:
        response = suggest_outline(req, llm_service=llm)

    assert response.status_code == 502
    assert json.loads(response.get_body())["error"] == "generation_failed"


def test_suggest_outline_requires_an_idea(request_factory):
    auth_patch, email_patch = _patched_auth()

    req = request_factory(method="POST", url="/api/manage/stories/suggest-outline", token="valid-token", body=json.dumps({}).encode())
    with auth_patch, email_patch:
        response = suggest_outline(req, llm_service=MagicMock())

    assert response.status_code == 422


# --- Listing ---


def test_list_stories_reflects_saved_stories_only(request_factory):
    story_service, _blob, _cosmos = _services()
    auth_patch, email_patch = _patched_auth()

    with auth_patch, email_patch:
        list_response = list_stories(request_factory(method="GET", url="/api/manage/stories", token="valid-token"), story_service=story_service)
    assert json.loads(list_response.get_body())["stories"] == []

    with auth_patch, email_patch:
        create_story(
            request_factory(method="POST", url="/api/manage/stories", token="valid-token", body=json.dumps({"name": "A Title"}).encode()),
            story_service=story_service,
        )

    with auth_patch, email_patch:
        list_response = list_stories(request_factory(method="GET", url="/api/manage/stories", token="valid-token"), story_service=story_service)
    stories = json.loads(list_response.get_body())["stories"]
    assert len(stories) == 1
    assert stories[0]["name"] == "A Title"
