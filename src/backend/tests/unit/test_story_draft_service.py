"""Unit tests for StoryDraftService: field writes never auto-generate, the explicit
`generate_story` action and its Completeness Rule guard, field validation, contradictory
answers, and malformed-generation handling (data-model.md, research.md §4, Edge Cases, #33)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.models.story import CharacterType, CompletionCriteria
from backend.models.story_draft import StoryDraft
from backend.services.llm_service import LLMOutputError, LLMRateLimitError
from backend.services.story_draft_service import (
    DraftIncompleteError,
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


def _complete_draft(draft_id="draft-1"):
    """A draft that already satisfies the Completeness Rule (data-model.md)."""
    return StoryDraft(
        id=draft_id,
        createdBy=CREATED_BY,
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin", description="Visiting for the summer.")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
    )


# --- Field writes never auto-generate (#33) ---


def test_patch_never_generates_even_when_all_four_conditions_are_now_met():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, name="The Lighthouse", worldPrompt="A lighthouse...")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    result_draft = service.patch_draft(
        "draft-1",
        {"characterTypes": _valid_character_types(), "completionCriteria": _valid_completion_criteria()},
    )

    assert result_draft.is_complete() is True
    llm.generate_story_config.assert_not_called()
    stories.create_story.assert_not_called()
    container.delete_item.assert_not_called()


def test_message_never_generates_even_when_all_four_conditions_are_now_met():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(
        id="draft-1",
        createdBy=CREATED_BY,
        name="The Lighthouse",
        worldPrompt="A lighthouse...",
        characterTypes=[],
        completionCriteria=None,
    )
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_exchange_response.return_value = {
        "assistantMessage": "Got it.",
        "fieldUpdates": {"characterTypes": _valid_character_types(), "completionCriteria": _valid_completion_criteria()},
    }

    result_draft = service.post_message("draft-1", "A curious cousin, and they must find the keeper.")

    assert result_draft.is_complete() is True
    llm.generate_story_config.assert_not_called()
    stories.create_story.assert_not_called()


# --- Explicit generate_story action ---


def test_generate_story_rejects_incomplete_draft():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="A lighthouse...")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(DraftIncompleteError):
        service.generate_story("draft-1")

    llm.generate_story_config.assert_not_called()


def test_generate_story_rejects_draft_missing_only_a_name():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(
        id="draft-1",
        createdBy=CREATED_BY,
        worldPrompt="A lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
    )
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(DraftIncompleteError):
        service.generate_story("draft-1")

    llm.generate_story_config.assert_not_called()


def test_generate_story_succeeds_once_complete():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _complete_draft()
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.return_value = {"narrativeGuidance": "Keep it eerie but safe."}
    generated_story = MagicMock(id="story-1")
    stories.create_story.return_value = generated_story

    story = service.generate_story("draft-1")

    assert story is generated_story
    stories.create_story.assert_called_once()
    container.delete_item.assert_called_once_with(item="draft-1", partition_key="draft-1")


def test_generate_story_returns_none_for_missing_draft():
    service, cosmos, llm, stories = _service()

    assert service.generate_story("nope") is None
    llm.generate_story_config.assert_not_called()


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

    result_draft = service.patch_draft("draft-1", {"characterTypes": _valid_character_types()})

    assert len(result_draft.characterTypes) == 1


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

    result_draft = service.post_message("draft-1", "Actually make it 1920.")

    assert result_draft.worldPrompt == "It is 1920."


# --- Malformed generation output leaves the draft intact ---


def test_malformed_generation_output_leaves_draft_intact_and_raises():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _complete_draft()
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.side_effect = LLMOutputError("bad json")

    with pytest.raises(GenerationFailedError):
        service.generate_story("draft-1")

    stories.create_story.assert_not_called()
    container.delete_item.assert_not_called()
    # generate_story never re-persists the draft itself — it only reads it; failure just
    # leaves whatever was already saved by the prior PATCH/message writes untouched.
    container.upsert_item.assert_not_called()


# --- Rate-limited generation leaves the draft intact (#33) ---


def test_rate_limited_generation_leaves_draft_intact_and_raises():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _complete_draft()
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.side_effect = LLMRateLimitError("rate limited")

    with pytest.raises(LLMRateLimitedError):
        service.generate_story("draft-1")

    stories.create_story.assert_not_called()
    container.delete_item.assert_not_called()


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
