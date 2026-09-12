"""Unit tests for StoryDraftService: field writes never auto-generate, the explicit
`generate_story` action and its Completeness Rule guard, field validation, contradictory
answers, and malformed-generation handling (data-model.md, research.md §4, Edge Cases, #33)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.models.story import CharacterType, CompletionCriteria
from backend.models.story_draft import StoryDraft
from backend.services.llm_service import LLMContentFilteredError, LLMOutputError, LLMRateLimitError
from backend.services.story_draft_service import (
    DraftIncompleteError,
    DraftNotFoundError,
    DraftValidationError,
    GenerationFailedError,
    LLMRateLimitedError,
    StoryDraftService,
    WrongDraftModeError,
)
from backend.services.story_service import DerivedContent, StaleStoryError
from backend.tests.conftest import _make_starting_point, _make_story

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


def test_world_prompt_suggestion_never_generates_even_when_all_four_conditions_are_now_met():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(
        id="draft-1",
        createdBy=CREATED_BY,
        name="The Lighthouse",
        characterTypes=[CharacterType.from_dict(ct) for ct in _valid_character_types()],
        completionCriteria=CompletionCriteria.from_dict(_valid_completion_criteria()),
    )
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse on a cold coast.", 12)

    result_draft = service.suggest_world_prompt("draft-1", "A lighthouse nobody has visited in years.")

    assert result_draft.is_complete() is True
    llm.generate_story_config.assert_not_called()
    stories.create_story.assert_not_called()


def test_world_prompt_suggestion_is_one_pass_and_writes_only_world_prompt():
    """#227 — one call per idea, no conversation, and no other draft field touched."""
    service, cosmos, llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, name="The Lighthouse", rules="Nobody gets hurt.")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.suggest_world_prompt.return_value = ("A half-abandoned lighthouse on a cold coast.", 12)

    result_draft = service.suggest_world_prompt("draft-1", "A lighthouse nobody has visited in years.")

    llm.suggest_world_prompt.assert_called_once()
    assert result_draft.worldPrompt == "A half-abandoned lighthouse on a cold coast."
    assert result_draft.name == "The Lighthouse"
    assert result_draft.rules == "Nobody gets hurt."
    assert result_draft.totalTokens == 12


def test_world_prompt_suggestion_accumulates_tokens_across_multiple_suggestions():
    service, cosmos, llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, totalTokens=12)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.suggest_world_prompt.return_value = ("A different lighthouse.", 8)

    result_draft = service.suggest_world_prompt("draft-1", "Try again.")

    assert result_draft.totalTokens == 20


def test_blank_idea_is_rejected_before_the_foundry_call():
    """A whitespace-only idea can neither spend tokens nor overwrite an existing prompt."""
    service, cosmos, llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="It is 1908.")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(DraftValidationError):
        service.suggest_world_prompt("draft-1", "   ")

    llm.suggest_world_prompt.assert_not_called()
    container.upsert_item.assert_not_called()


def test_blank_idea_starts_a_blank_draft_without_a_foundry_call():
    service, _cosmos, llm, _stories = _service()

    draft = service.create_draft(created_by=CREATED_BY, idea="   ")

    llm.suggest_world_prompt.assert_not_called()
    assert draft.worldPrompt is None


def test_empty_world_prompt_suggestion_leaves_the_existing_world_prompt_alone():
    service, cosmos, llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="It is 1908.")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.suggest_world_prompt.return_value = ("", 5)

    result_draft = service.suggest_world_prompt("draft-1", "Actually make it 1920.")

    assert result_draft.worldPrompt == "It is 1908."
    # The model was still consulted, so its tokens count even though the empty
    # suggestion itself is discarded (data-model.md → StoryDraft lifecycle).
    assert result_draft.totalTokens == 5


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
    llm.generate_story_config.return_value = ({"narrativeGuidance": "Keep it eerie but safe."}, 30)
    llm.generate_starting_point.return_value = (_make_starting_point().to_dict(), 40)
    generated_story = MagicMock(id="story-1")
    stories.create_story.return_value = generated_story

    story = service.generate_story("draft-1")

    assert story is generated_story
    # The opening scene is generated from the guidance that was just generated with it,
    # and persisted on the Story rather than regenerated per session (#271).
    llm.generate_starting_point.assert_called_once()
    assert llm.generate_starting_point.call_args[0][1] == "Keep it eerie but safe."
    stories.create_story.assert_called_once()
    assert stories.create_story.call_args[0][2] == _make_starting_point()
    # draft.totalTokens (0, since this draft was never given a suggestion) + both
    # generation calls' tokens (research.md Decision 2, creation case).
    assert stories.create_story.call_args[0][3] == 70
    container.delete_item.assert_called_once_with(item="draft-1", partition_key="draft-1")


def test_generate_story_folds_the_drafts_accumulated_tokens_into_the_story_total():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _complete_draft()
    draft.totalTokens = 15
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.return_value = ({"narrativeGuidance": "Keep it eerie but safe."}, 30)
    llm.generate_starting_point.return_value = (_make_starting_point().to_dict(), 40)
    stories.create_story.return_value = MagicMock(id="story-1")

    service.generate_story("draft-1")

    assert stories.create_story.call_args[0][3] == 15 + 30 + 40


@pytest.mark.parametrize("failure", [LLMOutputError("bad json"), LLMContentFilteredError("blocked")])
def test_generate_story_leaves_the_draft_intact_when_the_opening_scene_fails(failure):
    """A content-filtered opening scene is a failed generation like any other — the draft
    survives for another attempt rather than the call raising through (Copilot review,
    PR #279)."""
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _complete_draft()
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.generate_story_config.return_value = ({"narrativeGuidance": "Keep it eerie but safe."}, 30)
    llm.generate_starting_point.side_effect = failure

    with pytest.raises(GenerationFailedError):
        service.generate_story("draft-1")

    stories.create_story.assert_not_called()
    container.delete_item.assert_not_called()


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


def test_world_prompt_suggestion_overwrites_a_contradictory_earlier_answer():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, worldPrompt="It is 1908.")
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.suggest_world_prompt.return_value = ("It is 1920.", 10)

    result_draft = service.suggest_world_prompt("draft-1", "Actually make it 1920.")

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


def test_rate_limited_world_prompt_suggestion_raises_without_persisting():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    llm.suggest_world_prompt.side_effect = LLMRateLimitError("rate limited")

    with pytest.raises(LLMRateLimitedError):
        service.suggest_world_prompt("draft-1", "hello")

    container.upsert_item.assert_not_called()


# --- create_edit_draft / save_draft_to_story (012-story-editing-and-review) ---


def test_create_edit_draft_seeds_authored_fields_and_source_pinning():
    service, cosmos, _llm, _stories = _service()
    container = cosmos.get_container.return_value
    story = _make_story(
        id="story-1",
        name="The Sunken Library",
        worldPrompt="A flooded library.",
        characterTypes=[CharacterType(name="Archivist")],
        completionCriteria=CompletionCriteria(successConditions=["Recover the ledger"]),
        contentVersion=4,
    )

    draft = service.create_edit_draft(story, "admin-oid")

    assert draft.sourceStoryId == "story-1"
    assert draft.baseContentVersion == 4
    assert draft.name == "The Sunken Library"
    assert draft.worldPrompt == "A flooded library."
    assert draft.characterTypes == [CharacterType(name="Archivist")]
    assert draft.createdBy == "admin-oid"
    container.upsert_item.assert_called_once_with(draft.to_dict())


def _edit_draft(source_story_id="story-1", base_content_version=1, draft_id="draft-1"):
    return StoryDraft(
        id=draft_id,
        createdBy=CREATED_BY,
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        sourceStoryId=source_story_id,
        baseContentVersion=base_content_version,
    )


def test_save_draft_to_story_applies_and_deletes_the_draft():
    service, cosmos, llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft(base_content_version=2)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    story = _make_story(id="story-1", contentVersion=2)
    stories.get_story.return_value = story
    stories.derived_content.return_value = DerivedContent("Fresh guidance.", _make_starting_point(), [])
    updated_story = _make_story(id="story-1", contentVersion=3)
    stories.apply_content_write.return_value = updated_story

    result = service.save_draft_to_story("draft-1", "admin-oid")

    assert result is updated_story
    stories.apply_content_write.assert_called_once()
    args, kwargs = stories.apply_content_write.call_args
    assert args[0] is story
    assert args[2] == "admin-oid"
    assert args[3].narrativeGuidance == "Fresh guidance."
    assert args[3].startingPoint == _make_starting_point()
    container.delete_item.assert_called_once_with(item="draft-1", partition_key="draft-1")


def test_save_draft_to_story_folds_the_drafts_tokens_onto_the_derived_content_before_the_write():
    """research.md Decision 2 (edit case): the edit draft's own accumulated totalTokens
    (from suggest_world_prompt calls) must reach apply_content_write alongside the
    regeneration's own tokens — apply_content_write/_replaced_story then adds the combined
    total onto the story's existing totalTokens (T041), never replacing it."""
    service, cosmos, _llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft(base_content_version=2)
    draft.totalTokens = 12
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    story = _make_story(id="story-1", contentVersion=2)
    stories.get_story.return_value = story
    stories.derived_content.return_value = DerivedContent("Fresh guidance.", _make_starting_point(), [], tokens=30)

    service.save_draft_to_story("draft-1", "admin-oid")

    passed_derived = stories.apply_content_write.call_args[0][3]
    assert passed_derived.tokens == 12 + 30


def test_save_draft_to_story_carries_hand_edited_derived_fields_into_the_write():
    """A wizard save regenerates the derived fields it isn't given, so anything the
    administrator hand-edited in the configuration file is handed to the write explicitly
    rather than regenerated over (user review, PR #279)."""
    service, cosmos, _llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft(base_content_version=2)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    story = _make_story(
        id="story-1",
        contentVersion=2,
        narrativeGuidance="Hand-edited guidance.",
        adminEditedFields=["narrativeGuidance"],
    )
    stories.get_story.return_value = story
    stories.derived_content.return_value = DerivedContent("Hand-edited guidance.", _make_starting_point(), ["narrativeGuidance"])

    service.save_draft_to_story("draft-1", "admin-oid")

    # What "hand-edited" seeds into the configuration is StoryService's own rule
    # (test_story_service.py); the draft save's part is applying it before the write.
    carried_story, carried_configuration = stories.carry_admin_edits.call_args[0]
    assert carried_story is story
    assert carried_configuration is stories.derived_content.call_args[0][0]
    assert stories.derived_content.call_args[1]["existing"] is story


def test_save_draft_to_story_rejects_a_creation_draft():
    service, cosmos, _llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(WrongDraftModeError):
        service.save_draft_to_story("draft-1", "admin-oid")


def test_save_draft_to_story_returns_none_for_missing_draft():
    service, _cosmos, _llm, _stories = _service()

    assert service.save_draft_to_story("nope", "admin-oid") is None


def test_save_draft_to_story_raises_not_found_when_source_story_is_gone():
    service, cosmos, _llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft()
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    stories.get_story.return_value = None

    with pytest.raises(DraftNotFoundError):
        service.save_draft_to_story("draft-1", "admin-oid")


def test_save_draft_to_story_rejects_stale_base_content_version_and_leaves_draft_intact():
    service, cosmos, _llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft(base_content_version=1)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    stories.get_story.return_value = _make_story(id="story-1", contentVersion=2)

    with pytest.raises(StaleStoryError):
        service.save_draft_to_story("draft-1", "admin-oid")

    stories.apply_content_write.assert_not_called()
    container.delete_item.assert_not_called()


def test_save_draft_to_story_rejects_incomplete_draft():
    service, cosmos, _llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY, sourceStoryId="story-1", baseContentVersion=1)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(DraftIncompleteError):
        service.save_draft_to_story("draft-1", "admin-oid")

    stories.apply_content_write.assert_not_called()


def test_generate_story_rejects_an_edit_draft():
    service, cosmos, llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft()
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    with pytest.raises(WrongDraftModeError):
        service.generate_story("draft-1")

    llm.generate_story_config.assert_not_called()


# --- blurb (028-home-page-redesign FR-016) ---


def test_patch_accepts_blurb():
    service, cosmos, _llm, _stories = _service()
    container = cosmos.get_container.return_value
    draft = StoryDraft(id="draft-1", createdBy=CREATED_BY)
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()

    result_draft = service.patch_draft("draft-1", {"blurb": "Every door tells you a rule."})

    assert result_draft.blurb == "Every door tells you a rule."


def test_create_edit_draft_seeds_blurb_from_story():
    service, cosmos, _llm, _stories = _service()
    story = _make_story(blurb="Every door tells you a rule.")

    draft = service.create_edit_draft(story, "admin-oid")

    assert draft.blurb == "Every door tells you a rule."


def test_save_draft_to_story_carries_blurb_into_the_configuration():
    service, cosmos, _llm, stories = _service()
    container = cosmos.get_container.return_value
    draft = _edit_draft(base_content_version=2)
    draft.blurb = "Every door tells you a rule."
    container.read_item.side_effect = None
    container.read_item.return_value = draft.to_dict()
    story = _make_story(id="story-1", contentVersion=2)
    stories.get_story.return_value = story
    stories.derived_content.return_value = DerivedContent("Fresh guidance.", _make_starting_point(), [])
    stories.apply_content_write.return_value = _make_story(id="story-1", contentVersion=3)

    service.save_draft_to_story("draft-1", "admin-oid")

    args, _kwargs = stories.apply_content_write.call_args
    configuration = args[1]
    assert configuration.blurb == "Every door tells you a rule."
