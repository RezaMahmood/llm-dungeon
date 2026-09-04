"""Unit tests for ProvisionedAccountEntry, Story, StoryDraft, CharacterType, and
CompletionCriteria model validation."""

from __future__ import annotations

import pytest

from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.models.story_draft import StoryCreationExchange, StoryDraft


def test_provisioned_account_entry_rejects_empty_roles():
    with pytest.raises(ValueError):
        ProvisionedAccountEntry(email="player@example.com", roles=[])


def test_provisioned_account_entry_rejects_unrecognized_role():
    with pytest.raises(ValueError):
        ProvisionedAccountEntry(email="player@example.com", roles=["SuperAdmin"])


def test_provisioned_account_entry_lowercases_email_and_id():
    entry = ProvisionedAccountEntry(email="Player@Example.com", roles=["Player"])
    assert entry.email == "player@example.com"
    assert entry.id == "player@example.com"


def test_provisioned_account_entry_id_matches_email_when_explicit():
    entry = ProvisionedAccountEntry(email="Player@Example.com", roles=["Player"], id="Player@Example.com")
    assert entry.id == entry.email == "player@example.com"


def test_provisioned_account_entry_round_trips_through_dict():
    entry = ProvisionedAccountEntry(
        email="admin@example.com",
        roles=["Administrator"],
        objectId="oid-1",
        dateAdded="2026-08-29T00:00:00Z",
        addedBy="seed",
        dateBound="2026-08-29T00:05:00Z",
    )
    restored = ProvisionedAccountEntry.from_dict(entry.to_dict())
    assert restored == entry


# --- CharacterType ---


def test_character_type_rejects_empty_name():
    with pytest.raises(ValueError):
        CharacterType(name="")


def test_character_type_accepts_name_only():
    ct = CharacterType(name="Curious Cousin")
    assert ct.description is None


# --- CompletionCriteria ---


def test_completion_criteria_rejects_empty_success_conditions():
    with pytest.raises(ValueError):
        CompletionCriteria(successConditions=[])


def test_completion_criteria_rejects_missing_rule_with_multiple_conditions():
    with pytest.raises(ValueError):
        CompletionCriteria(
            successConditions=["Find the keeper"],
            failureConditions=["The player leaves the cove"],
        )


def test_completion_criteria_accepts_single_condition_with_no_rule():
    criteria = CompletionCriteria(successConditions=["Find the keeper"])
    assert criteria.rule is None


def test_completion_criteria_accepts_multiple_conditions_with_rule():
    criteria = CompletionCriteria(
        successConditions=["Find the keeper"],
        failureConditions=["The player leaves the cove"],
        rule="any",
    )
    assert criteria.rule == "any"


def test_completion_criteria_round_trips_through_dict():
    criteria = CompletionCriteria(
        successConditions=["Find the keeper"],
        failureConditions=["The player leaves the cove"],
        maxDurationMinutes=20,
        rule="all",
    )
    restored = CompletionCriteria.from_dict(criteria.to_dict())
    assert restored == criteria


# --- Story ---


def _completion_criteria() -> CompletionCriteria:
    return CompletionCriteria(successConditions=["Find the keeper"])


def test_story_accepts_single_character_type():
    story = Story(
        id="story-1",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=_completion_criteria(),
        narrativeGuidance="Keep it eerie but never actually dangerous.",
        createdBy="oid-1",
        createdAt="2026-08-29T20:04:00Z",
        contentUpdatedAt="2026-08-29T20:04:00Z",
    )
    assert len(story.characterTypes) == 1
    assert story.published is False


def test_story_rejects_empty_character_types():
    with pytest.raises(ValueError):
        Story(
            id="story-1",
            worldPrompt="A half-abandoned lighthouse...",
            characterTypes=[],
            completionCriteria=_completion_criteria(),
            narrativeGuidance="Keep it eerie but never actually dangerous.",
            createdBy="oid-1",
            createdAt="2026-08-29T20:04:00Z",
            contentUpdatedAt="2026-08-29T20:04:00Z",
        )


def test_story_rejects_empty_world_prompt():
    with pytest.raises(ValueError):
        Story(
            id="story-1",
            worldPrompt="",
            characterTypes=[CharacterType(name="Curious Cousin")],
            completionCriteria=_completion_criteria(),
            narrativeGuidance="Keep it eerie but never actually dangerous.",
            createdBy="oid-1",
            createdAt="2026-08-29T20:04:00Z",
            contentUpdatedAt="2026-08-29T20:04:00Z",
        )


def test_story_round_trips_through_dict():
    story = Story(
        id="story-1",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin", description="Visiting for the summer.")],
        completionCriteria=_completion_criteria(),
        narrativeGuidance="Keep it eerie but never actually dangerous.",
        createdBy="oid-1",
        createdAt="2026-08-29T20:04:00Z",
        contentUpdatedAt="2026-08-29T20:04:00Z",
        name="The Lighthouse at Gullwing Cove",
    )
    restored = Story.from_dict(story.to_dict())
    assert restored == story


# --- StoryDraft ---


def test_story_draft_completeness_rule_requires_all_four_conditions():
    draft = StoryDraft(id="draft-1", createdBy="oid-1")
    assert draft.is_complete() is False

    draft.name = "The Lighthouse at Gullwing Cove"
    assert draft.is_complete() is False

    draft.worldPrompt = "A half-abandoned lighthouse..."
    assert draft.is_complete() is False

    draft.characterTypes = [CharacterType(name="Curious Cousin")]
    assert draft.is_complete() is False

    draft.completionCriteria = _completion_criteria()
    assert draft.is_complete() is True


def test_story_draft_touch_refreshes_updated_at_and_ttl():
    draft = StoryDraft(id="draft-1", createdBy="oid-1", updatedAt="2000-01-01T00:00:00Z", ttl=1)
    draft.touch()
    assert draft.updatedAt != "2000-01-01T00:00:00Z"
    assert draft.ttl == 86400


def test_story_draft_round_trips_through_dict():
    draft = StoryDraft(
        id="draft-1",
        createdBy="oid-1",
        worldPrompt="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=_completion_criteria(),
        exchanges=[StoryCreationExchange(role="administrator", message="A half-abandoned lighthouse...")],
    )
    restored = StoryDraft.from_dict(draft.to_dict())
    assert restored == draft


def test_story_creation_exchange_rejects_invalid_role():
    with pytest.raises(ValueError):
        StoryCreationExchange(role="narrator", message="hello")
