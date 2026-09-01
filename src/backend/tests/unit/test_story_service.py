"""Unit tests for StoryService: default published=False (FR-006), summary-only listing,
and full-detail get-by-id."""

from __future__ import annotations

from unittest.mock import MagicMock

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.models.story import CharacterType, CompletionCriteria
from backend.models.story_draft import StoryDraft
from backend.services.story_service import StoryService


def _draft() -> StoryDraft:
    return StoryDraft(
        id="draft-1",
        createdBy="oid-1",
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
    )


def test_create_story_defaults_to_unpublished():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    story = service.create_story(_draft(), "Keep it eerie but safe.")

    assert story.published is False
    cosmos.get_container.return_value.upsert_item.assert_called_once_with(story.to_dict())


def test_list_summaries_returns_summary_shape_only():
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {"id": "story-1", "name": "The Lighthouse at Gullwing Cove", "published": False, "createdAt": "2026-08-29T20:04:00Z"}
    ]
    service = StoryService(cosmos_service=cosmos)

    summaries = service.list_summaries()

    assert summaries == [
        {"id": "story-1", "name": "The Lighthouse at Gullwing Cove", "published": False, "createdAt": "2026-08-29T20:04:00Z"}
    ]


def test_get_story_returns_full_config_including_narrative_guidance():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    fetched = service.get_story(story.id)

    assert fetched.narrativeGuidance == "Keep it eerie but safe."
    assert fetched == story


def test_get_story_returns_none_when_not_found():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.get_story("missing") is None


# --- Publish gate (FR-008) ---


def test_create_story_stamps_content_updated_at_and_leaves_gate_fields_null():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    story = service.create_story(_draft(), "Keep it eerie but safe.")

    assert story.contentUpdatedAt == story.createdAt
    assert story.lastTestPlayedAt is None
    assert story.lastPublishedAt is None


def test_publish_is_blocked_when_never_test_played():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    published_story, gate_satisfied = service.publish(story.id)

    assert gate_satisfied is False
    assert published_story.published is False
    assert published_story.lastPublishedAt is None


def test_publish_is_blocked_when_test_played_before_content_last_changed():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    story.lastTestPlayedAt = "2020-01-01T00:00:00Z"  # before contentUpdatedAt
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    _published_story, gate_satisfied = service.publish(story.id)

    assert gate_satisfied is False


def test_publish_succeeds_once_gate_satisfied_and_stamps_last_published_at():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    story.lastTestPlayedAt = "2099-01-01T00:00:00Z"  # at/after contentUpdatedAt
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    published_story, gate_satisfied = service.publish(story.id)

    assert gate_satisfied is True
    assert published_story.published is True
    assert published_story.lastPublishedAt is not None


def test_publish_returns_none_for_unknown_story():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    story, gate_satisfied = service.publish("missing")

    assert story is None
    assert gate_satisfied is False


def test_publish_is_idempotent_and_restamps_last_published_at():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    story.lastTestPlayedAt = "2099-01-01T00:00:00Z"
    story.published = True
    story.lastPublishedAt = "2020-01-01T00:00:00Z"
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    published_story, gate_satisfied = service.publish(story.id)

    assert gate_satisfied is True
    assert published_story.published is True
    assert published_story.lastPublishedAt != "2020-01-01T00:00:00Z"


def test_unpublish_clears_published_but_retains_last_published_at():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    story.published = True
    story.lastPublishedAt = "2026-08-30T14:22:00Z"
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    unpublished_story = service.unpublish(story.id)

    assert unpublished_story.published is False
    assert unpublished_story.lastPublishedAt == "2026-08-30T14:22:00Z"


def test_unpublish_already_unpublished_story_is_idempotent():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    story = service.create_story(_draft(), "Keep it eerie but safe.")
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    unpublished_story = service.unpublish(story.id)

    assert unpublished_story.published is False


def test_unpublish_returns_none_for_unknown_story():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.unpublish("missing") is None
