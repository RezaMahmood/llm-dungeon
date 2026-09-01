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
