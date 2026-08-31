"""Unit tests for StoryService: explicit create/update Save semantics (FR-004), audit
fields (FR-012), Abandon delete (FR-013/014), cover-image upload (FR-009), default
published=False (FR-006), summary-only listing, and full-detail get-by-id."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.services.story_service import StoryService, StoryValidationError

ADMIN_EMAIL = "admin@example.com"
OTHER_ADMIN_EMAIL = "editor@example.com"


def test_create_story_requires_only_a_name_and_defaults_to_unpublished():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    story = service.create_story("The Lighthouse at Gullwing Cove", ADMIN_EMAIL)

    assert story.published is False
    assert story.createdBy == ADMIN_EMAIL
    assert story.updatedBy == ADMIN_EMAIL
    assert story.createdAt == story.updatedAt
    cosmos.get_container.return_value.upsert_item.assert_called_once_with(story.to_dict())


def test_create_story_rejects_missing_name():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    with pytest.raises(StoryValidationError):
        service.create_story("", ADMIN_EMAIL)


def test_create_story_accepts_additional_fields_without_requiring_completeness():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    story = service.create_story("A Title", ADMIN_EMAIL, {"outline": "A half-abandoned lighthouse..."})

    assert story.outline == "A half-abandoned lighthouse..."
    assert story.characterTypes == []
    assert story.completionCriteria is None


def test_update_story_stamps_updated_by_and_updated_at():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story("A Title", ADMIN_EMAIL)
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    updated = service.update_story(story.id, OTHER_ADMIN_EMAIL, {"outline": "Updated outline"})

    assert updated.outline == "Updated outline"
    assert updated.updatedBy == OTHER_ADMIN_EMAIL
    assert updated.createdBy == ADMIN_EMAIL


def test_update_story_returns_none_when_story_does_not_exist():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.update_story("missing", ADMIN_EMAIL, {"outline": "x"}) is None


def test_update_story_rejects_invalid_character_types():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story("A Title", ADMIN_EMAIL)
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    with pytest.raises(StoryValidationError):
        service.update_story(story.id, ADMIN_EMAIL, {"characterTypes": [{"description": "missing a name"}]})


def test_update_story_rejects_completion_criteria_missing_rule_with_multiple_conditions():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story("A Title", ADMIN_EMAIL)
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    with pytest.raises(StoryValidationError):
        service.update_story(
            story.id,
            ADMIN_EMAIL,
            {"completionCriteria": {"successConditions": ["Find the keeper"], "failureConditions": ["Give up"]}},
        )


def test_delete_story_removes_a_persisted_story():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    service.delete_story("story-1")

    cosmos.get_container.return_value.delete_item.assert_called_once_with(item="story-1", partition_key="story-1")


def test_delete_story_is_a_no_op_when_nothing_exists():
    cosmos = MagicMock()
    cosmos.get_container.return_value.delete_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    service.delete_story("never-saved")  # must not raise


def test_upload_cover_image_stores_blob_url_reference():
    cosmos = MagicMock()
    blob = MagicMock()
    blob.upload_cover_image.return_value = "https://example.blob.core.windows.net/assets/story-covers/story-1/cover.png"
    service = StoryService(cosmos_service=cosmos, blob_service=blob)
    story = service.create_story("A Title", ADMIN_EMAIL)
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    updated = service.upload_cover_image(story.id, ADMIN_EMAIL, "cover.png", b"fake-bytes", "image/png")

    blob.upload_cover_image.assert_called_once_with(story.id, "cover.png", b"fake-bytes", "image/png")
    assert updated.coverImageUrl == "https://example.blob.core.windows.net/assets/story-covers/story-1/cover.png"


def test_upload_cover_image_returns_none_when_story_does_not_exist():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos, blob_service=MagicMock())

    assert service.upload_cover_image("missing", ADMIN_EMAIL, "cover.png", b"x", "image/png") is None


def test_list_summaries_returns_summary_shape_only():
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {"id": "story-1", "name": "The Lighthouse at Gullwing Cove", "published": False, "createdAt": "2026-08-30T20:04:00Z"}
    ]
    service = StoryService(cosmos_service=cosmos)

    summaries = service.list_summaries()

    assert summaries == [
        {"id": "story-1", "name": "The Lighthouse at Gullwing Cove", "published": False, "createdAt": "2026-08-30T20:04:00Z"}
    ]


def test_get_story_returns_full_config():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story("A Title", ADMIN_EMAIL)
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    fetched = service.get_story(story.id)

    assert fetched == story


def test_get_story_returns_none_when_not_found():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.get_story("missing") is None
