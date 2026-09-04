"""Unit tests for StoryService: default published=False (FR-006), summary-only listing,
and full-detail get-by-id."""

from __future__ import annotations

from unittest.mock import MagicMock

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.models.story_draft import StoryDraft
from backend.services.story_service import PUBLISH_GATE_NOT_SATISFIED, StoryService


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
    assert story.contentUpdatedAt == story.createdAt
    assert story.lastPublishedAt is None
    assert story.lastTestPlayedAt is None
    cosmos.get_container.return_value.upsert_item.assert_called_once_with(story.to_dict())


def test_list_summaries_returns_summary_shape_only():
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {
            "id": "story-1",
            "name": "The Lighthouse at Gullwing Cove",
            "published": False,
            "lastPublishedAt": None,
            "createdAt": "2026-08-29T20:04:00Z",
        }
    ]
    service = StoryService(cosmos_service=cosmos)

    summaries = service.list_summaries()

    assert summaries == [
        {
            "id": "story-1",
            "name": "The Lighthouse at Gullwing Cove",
            "published": False,
            "lastPublishedAt": None,
            "createdAt": "2026-08-29T20:04:00Z",
        }
    ]
    query_args = cosmos.query.call_args[0]
    assert "c.lastPublishedAt" in query_args[1]


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


def _story(**overrides) -> Story:
    defaults = dict(
        id="story-1",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        narrativeGuidance="Keep it eerie but safe.",
        createdBy="admin-oid",
        createdAt="2026-08-30T00:00:00Z",
        contentUpdatedAt="2026-08-30T00:00:00Z",
    )
    defaults.update(overrides)
    return Story(**defaults)


def _service_with(story: Story, cosmos=None) -> StoryService:
    cosmos = cosmos or MagicMock()
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()
    service = StoryService(cosmos_service=cosmos)
    return service


# --- can_publish / publish / unpublish (FR-003, FR-004, FR-006, FR-008, FR-012) ---


def test_can_publish_is_false_when_never_test_played():
    service = StoryService(cosmos_service=MagicMock())
    story = _story(lastTestPlayedAt=None)

    assert service.can_publish(story) is False


def test_can_publish_is_false_when_test_played_before_content_updated():
    service = StoryService(cosmos_service=MagicMock())
    story = _story(contentUpdatedAt="2026-08-30T10:00:00Z", lastTestPlayedAt="2026-08-30T09:00:00Z")

    assert service.can_publish(story) is False


def test_can_publish_is_true_when_test_played_at_or_after_content_updated():
    service = StoryService(cosmos_service=MagicMock())
    story = _story(contentUpdatedAt="2026-08-30T09:00:00Z", lastTestPlayedAt="2026-08-30T09:00:00Z")

    assert service.can_publish(story) is True


def test_publish_returns_none_for_missing_story():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.publish("missing") is None


def test_publish_returns_gate_sentinel_when_gate_not_satisfied():
    story = _story(lastTestPlayedAt=None)
    service = _service_with(story)

    result = service.publish(story.id)

    assert result is PUBLISH_GATE_NOT_SATISFIED
    service._container().upsert_item.assert_not_called()


def test_publish_sets_published_and_stamps_last_published_at_when_gate_satisfied():
    story = _story(contentUpdatedAt="2026-08-30T09:00:00Z", lastTestPlayedAt="2026-08-30T09:00:00Z")
    service = _service_with(story)

    result = service.publish(story.id)

    assert result.published is True
    assert result.lastPublishedAt is not None
    service._container().upsert_item.assert_called_once_with(result.to_dict())


def test_redundant_publish_restamps_last_published_at_and_succeeds():
    story = _story(
        contentUpdatedAt="2026-08-30T09:00:00Z",
        lastTestPlayedAt="2026-08-30T09:00:00Z",
        published=True,
        lastPublishedAt="2026-08-30T09:05:00Z",
    )
    service = _service_with(story)

    result = service.publish(story.id)

    assert result.published is True
    assert result.lastPublishedAt is not None


def test_unpublish_sets_published_false_and_leaves_last_published_at_unchanged():
    story = _story(published=True, lastPublishedAt="2026-08-30T09:05:00Z")
    service = _service_with(story)

    result = service.unpublish(story.id)

    assert result.published is False
    assert result.lastPublishedAt == "2026-08-30T09:05:00Z"
    service._container().upsert_item.assert_called_once_with(result.to_dict())


def test_redundant_unpublish_is_a_no_op_success():
    story = _story(published=False, lastPublishedAt="2026-08-30T09:05:00Z")
    service = _service_with(story)

    result = service.unpublish(story.id)

    assert result.published is False
    assert result.lastPublishedAt == "2026-08-30T09:05:00Z"


def test_unpublish_returns_none_for_missing_story():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.unpublish("missing") is None


def test_list_published_summaries_returns_adventure_summary_shape():
    """006-adventure-and-character-setup FR-001/FR-006: only published==true rows, in the
    AdventureSummary shape (data-model.md), never the admin `published`/`createdAt` fields."""
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {
            "id": "story-1",
            "name": "Nine Doors of Mudlark Hall",
            "tone": "Mystery",
            "sessionLengthMinutes": 20,
            "readingLevel": "Year 5",
        }
    ]
    service = StoryService(cosmos_service=cosmos)

    summaries = service.list_published_summaries()

    assert summaries == [
        {
            "id": "story-1",
            "name": "Nine Doors of Mudlark Hall",
            "tone": "Mystery",
            "sessionLengthMinutes": 20,
            "readingLevel": "Year 5",
        }
    ]
    query_args = cosmos.query.call_args[0]
    assert "c.published = true" in query_args[1]
    assert "c.name" in query_args[1] and "c.tone" in query_args[1]
    assert "c.published" not in query_args[1].split("WHERE")[0]
    assert "c.createdAt" not in query_args[1]
