"""Unit tests for StoryDraftService: Completeness Rule, field validation, contradictory
answers, and malformed-generation handling (data-model.md, research.md §4, Edge Cases)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.models.story_draft import StoryDraft
from backend.services.llm_service import LLMOutputError, LLMRateLimitError
from backend.services.story_draft_service import (
    DraftValidationError,
    GenerationFailedError,
    LLMRateLimitedError,
    StoryDraftService,
)

CREATED_BY = "oid-1"


def _service(cosmos=None, llm=None, stories=None):
    cosmos = cosmos or MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    llm = llm or MagicMock()
    stories = stories or MagicMock()
    return StoryDraftService(cosmos_service=cosmos, llm_service=llm, story_service=stories), cosmos, llm, stories


def _valid_character_types():
    return [{"name": "Curious Cousin", "description": "Visiting for the summer."}]


def _valid_completion_criteria():
    return {"successConditions": ["Find the keeper"], "failureConditions": [], "rule": None}


# --- Completeness Rule ---


def test_patch_does_not_generate_until_all_three_conditions_met():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    result_draft, story = service.patch_draft("draft-1", {"worldPrompt": "A lighthouse..."})

    assert story is None
    assert result_draft.is_complete() is False
    llm.generate_story_config.assert_not_called()


def test_patch_triggers_generation_when_all_three_conditions_met():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="A lighthouse...")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.return_value = {"narrativeGuidance": "Keep it eerie but safe."}
    generated_story = MagicMock(id="story-1")
    stories.create_story.return_value = generated_story

    result_draft, story = service.patch_draft(
        "draft-1",
        {"characterTypes": _valid_character_types(), "completionCriteria": _valid_completion_criteria()},
    )

    assert story is generated_story
    stories.create_story.assert_called_once()
    container.delete_item.assert_called_once_with(item="draft-1", partition_key="draft-1")


# --- Field validation rejection ---


def test_patch_rejects_empty_success_conditions():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(DraftValidationError):
        service.patch_draft("draft-1", {"completionCriteria": {"successConditions": []}})

    container.upsert_item.assert_not_called()


def test_patch_rejects_missing_rule_with_multiple_conditions():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(DraftValidationError):
        service.patch_draft(
            "draft-1",
            {
                "completionCriteria": {
                    "successConditions": ["Find the keeper"],
                    "failureConditions": ["Leave the cove"],
                }
            },
        )


# --- Single character type acceptance ---


def test_patch_accepts_single_character_type():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    result_draft, story = service.patch_draft("draft-1", {"characterTypes": _valid_character_types()})

    assert len(result_draft.characterTypes) == 1
    assert story is None  # still missing worldPrompt/completionCriteria


# --- Contradictory-answer overwrite (latest wins) ---


def test_message_field_updates_overwrite_a_contradictory_earlier_answer():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="It is 1908.")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_exchange_response.return_value = {
        "assistantMessage": "Got it, updated to 1920.",
        "fieldUpdates": {"worldPrompt": "It is 1920."},
    }

    result_draft, _story = service.post_message("draft-1", "Actually make it 1920.")

    assert result_draft.worldPrompt == "It is 1920."


# --- Malformed generation output leaves the draft intact ---


def test_malformed_generation_output_leaves_draft_intact_and_raises():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(
        id="draft-1",
        createdBy=CREATED_BY,
        worldPrompt="A lighthouse...",
    )
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.side_effect = LLMOutputError("bad json")

    with pytest.raises(GenerationFailedError):
        service.patch_draft(
            "draft-1",
            {"characterTypes": _valid_character_types(), "completionCriteria": _valid_completion_criteria()},
        )

    stories.create_story.assert_not_called()
    container.delete_item.assert_not_called()
    # The draft write still happens (touch/TTL refresh) but no Story was created.
    container.upsert_item.assert_called_once()


# --- Rate-limited generation leaves the draft intact (#33) ---


def test_rate_limited_generation_leaves_draft_intact_and_raises():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="A lighthouse...")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.side_effect = LLMRateLimitError("rate limited")

    with pytest.raises(LLMRateLimitedError):
        service.patch_draft(
            "draft-1",
            {"characterTypes": _valid_character_types(), "completionCriteria": _valid_completion_criteria()},
        )

    stories.create_story.assert_not_called()
    container.delete_item.assert_not_called()
    container.upsert_item.assert_called_once()


def test_rate_limited_exchange_raises_without_persisting():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_exchange_response.side_effect = LLMRateLimitError("rate limited")

    with pytest.raises(LLMRateLimitedError):
        service.post_message("draft-1", "hello")

    container.upsert_item.assert_not_called()
