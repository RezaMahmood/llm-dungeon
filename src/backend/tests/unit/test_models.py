"""Unit tests for ProvisionedAccountEntry, Story, StoryDraft, CharacterType, and
CompletionCriteria model validation."""

from __future__ import annotations

import pytest

from backend.models.play_session import PlayerInteraction, PlaySession
from backend.models.player_content_safety_standing import PlayerContentSafetyStanding
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


def test_story_from_dict_defaults_content_updated_at_to_created_at_for_pre_existing_rows():
    """Story rows persisted before this feature added contentUpdatedAt must still be
    readable after deploy — falling back to createdAt is the correct interim value
    (it predates 017's edit-tracking path, so createdAt is the only known "content set" time)."""
    data = {
        "id": "story-1",
        "worldPrompt": "A half-abandoned lighthouse...",
        "characterTypes": [{"name": "Curious Cousin", "description": None}],
        "completionCriteria": {"successConditions": ["Find the keeper"], "maxDurationMinutes": None, "failureConditions": [], "rule": None},
        "narrativeGuidance": "Keep it eerie but never actually dangerous.",
        "createdBy": "oid-1",
        "createdAt": "2026-08-29T20:04:00Z",
    }

    story = Story.from_dict(data)

    assert story.contentUpdatedAt == "2026-08-29T20:04:00Z"


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


# --- PlayerInteraction / PlaySession (008-core-gameplay) ---


def _opening_turn() -> PlayerInteraction:
    return PlayerInteraction(
        turnNumber=0,
        narrativeText="The lighthouse door creaks open.",
        suggestedActions=["look around", "step inside"],
        locationLabel="Lighthouse entrance",
        timestamp="2026-09-05T00:00:00Z",
    )


def test_player_interaction_round_trips_through_dict():
    turn = PlayerInteraction(
        turnNumber=1,
        playerInput="look around",
        narrativeText="A spiral of stairs climbs into the dark.",
        suggestedActions=["climb the stairs", "call out"],
        locationLabel="Lighthouse base",
        goalLabel="Find the keeper",
        progress={"current": 1, "total": 5},
        timestamp="2026-09-05T00:01:00Z",
    )
    restored = PlayerInteraction.from_dict(turn.to_dict())
    assert restored == turn


def test_play_session_defaults_is_active_for_player_true():
    session = PlaySession(
        id="session-1",
        adventureId="story-1",
        playerId="oid-1",
        characterName="Wren",
        characterType="Detective",
        startedAt="2026-09-05T00:00:00Z",
        lastInteractionAt="2026-09-05T00:00:00Z",
        turns=[_opening_turn()],
    )
    assert session.isActiveForPlayer is True
    assert session.status == "active"
    assert session.summary is None
    assert session.summarizedThroughTurn == 0


def test_play_session_round_trips_through_dict():
    session = PlaySession(
        id="session-1",
        adventureId="story-1",
        playerId="oid-1",
        characterName="Wren",
        characterType="Detective",
        startedAt="2026-09-05T00:00:00Z",
        lastInteractionAt="2026-09-05T00:05:00Z",
        turns=[_opening_turn()],
        satisfiedSuccessConditions=[0],
        completionReason={"type": "success", "detail": "Found the ninth door"},
        status="concluded",
        endedAt="2026-09-05T00:10:00Z",
        summary="A brief recap.",
        summarizedThroughTurn=20,
        isActiveForPlayer=False,
    )
    restored = PlaySession.from_dict(session.to_dict())
    assert restored == session


# --- PlayerContentSafetyStanding (008-core-gameplay) ---


def test_player_content_safety_standing_defaults():
    standing = PlayerContentSafetyStanding(id="oid-1")
    assert standing.flaggedCount == 0
    assert standing.lockoutUntil is None


def test_player_content_safety_standing_round_trips_through_dict():
    standing = PlayerContentSafetyStanding(id="oid-1", flaggedCount=3, lockoutUntil="2026-09-05T01:00:00Z")
    restored = PlayerContentSafetyStanding.from_dict(standing.to_dict())
    assert restored == standing
