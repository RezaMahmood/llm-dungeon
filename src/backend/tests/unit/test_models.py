"""Unit tests for ProvisionedAccountEntry, Story, CharacterType, and CompletionCriteria
model validation."""

from __future__ import annotations

import pytest

from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.models.story import CharacterType, CompletionCriteria, Story


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
#
# Only `name` is required (FR-004, FR-009) — Save is available at any point in the
# wizard, not gated on completeness, so every other field must accept being absent.


def test_story_requires_only_a_name():
    story = Story(
        id="story-1",
        name="The Lighthouse at Gullwing Cove",
        createdBy="admin@example.com",
        createdAt="2026-08-30T20:04:00Z",
        updatedBy="admin@example.com",
        updatedAt="2026-08-30T20:04:00Z",
    )
    assert story.outline is None
    assert story.characterTypes == []
    assert story.completionCriteria is None
    assert story.published is False


def test_story_rejects_empty_name():
    with pytest.raises(ValueError):
        Story(
            id="story-1",
            name="",
            createdBy="admin@example.com",
            createdAt="2026-08-30T20:04:00Z",
            updatedBy="admin@example.com",
            updatedAt="2026-08-30T20:04:00Z",
        )


def test_story_accepts_full_configuration():
    story = Story(
        id="story-1",
        name="The Lighthouse at Gullwing Cove",
        createdBy="admin@example.com",
        createdAt="2026-08-30T20:04:00Z",
        updatedBy="admin@example.com",
        updatedAt="2026-08-30T20:05:00Z",
        outline="A half-abandoned lighthouse...",
        rules="Nobody actually gets hurt.",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
        coverImageUrl="https://example.blob.core.windows.net/assets/story-covers/story-1/cover.png",
    )
    assert len(story.characterTypes) == 1
    assert story.published is False


def test_story_round_trips_through_dict():
    story = Story(
        id="story-1",
        name="The Lighthouse at Gullwing Cove",
        createdBy="admin@example.com",
        createdAt="2026-08-30T20:04:00Z",
        updatedBy="editor@example.com",
        updatedAt="2026-08-30T20:05:00Z",
        outline="A half-abandoned lighthouse...",
        characterTypes=[CharacterType(name="Curious Cousin", description="Visiting for the summer.")],
        completionCriteria=CompletionCriteria(successConditions=["Find the keeper"]),
    )
    restored = Story.from_dict(story.to_dict())
    assert restored == story
