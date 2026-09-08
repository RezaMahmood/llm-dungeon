"""Unit tests for StoryService: default published=False (FR-006), summary-only listing,
and full-detail get-by-id."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from backend.models.story import CharacterType, CompletionCriteria, Story
from backend.models.story_draft import StoryDraft
from backend.services.story_service import (
    PUBLISH_GATE_NOT_SATISFIED,
    ConfirmationRequiredError,
    DerivedContent,
    StaleStoryError,
    StoryNotFoundError,
    StoryService,
    TitleRequiredError,
    WriteConflictError,
)
from backend.tests.conftest import _make_starting_point as _starting_point
from backend.tests.conftest import _make_story as _story


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

    story = service.create_story(_draft(), "Keep it eerie but safe.", _starting_point())

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
    story = service.create_story(_draft(), "Keep it eerie but safe.", _starting_point())
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()

    fetched = service.get_story(story.id)

    assert fetched.narrativeGuidance == "Keep it eerie but safe."
    assert fetched == story


def test_get_story_returns_none_when_not_found():
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.get_story("missing") is None


def test_get_story_name_returns_name_via_projected_query():
    cosmos = MagicMock()
    cosmos.query.return_value = [{"name": "The Lighthouse at Gullwing Cove"}]
    service = StoryService(cosmos_service=cosmos)

    name = service.get_story_name("story-1")

    assert name == "The Lighthouse at Gullwing Cove"
    call_args, call_kwargs = cosmos.query.call_args
    assert "SELECT c.name" in call_args[1]
    assert call_kwargs["partition_key"] == "story-1"


def test_get_story_name_returns_none_when_not_found():
    cosmos = MagicMock()
    cosmos.query.return_value = []
    service = StoryService(cosmos_service=cosmos)

    assert service.get_story_name("missing") is None


def test_get_story_name_returns_none_when_row_is_missing_the_name_field():
    """A row without `name` must fall back to `None` (the caller's cue to show
    "Adventure") rather than raising KeyError."""
    cosmos = MagicMock()
    cosmos.query.return_value = [{}]
    service = StoryService(cosmos_service=cosmos)

    assert service.get_story_name("story-1") is None


def test_get_adventure_summary_returns_projected_fields_only():
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {
            "id": "story-1",
            "name": "The Lighthouse at Gullwing Cove",
            "published": True,
            "characterTypes": [{"name": "Curious Cousin", "description": None}],
        }
    ]
    service = StoryService(cosmos_service=cosmos)

    summary = service.get_adventure_summary("story-1")

    assert summary == {
        "id": "story-1",
        "name": "The Lighthouse at Gullwing Cove",
        "published": True,
        "characterTypes": [{"name": "Curious Cousin", "description": None}],
    }
    call_args, call_kwargs = cosmos.query.call_args
    assert "c.worldPrompt" not in call_args[1]
    assert "c.narrativeGuidance" not in call_args[1]
    assert call_kwargs["partition_key"] == "story-1"


def test_get_adventure_summary_returns_none_when_not_found():
    cosmos = MagicMock()
    cosmos.query.return_value = []
    service = StoryService(cosmos_service=cosmos)

    assert service.get_adventure_summary("missing") is None


def test_get_adventure_summary_defaults_published_to_false_for_a_legacy_row():
    """A row without `published` (Story.from_dict()'s own default) must not raise
    KeyError, and must default to `False` rather than truthy-by-presence."""
    cosmos = MagicMock()
    cosmos.query.return_value = [
        {"id": "story-1", "name": "The Lighthouse at Gullwing Cove", "characterTypes": []}
    ]
    service = StoryService(cosmos_service=cosmos)

    summary = service.get_adventure_summary("story-1")

    assert summary["published"] is False


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


# --- apply_content_write / import_configuration (012-story-editing-and-review) ---


class _EtagContainer:
    """Minimal Cosmos fake supporting the `_etag` precondition dance
    (research.md §6, mirroring play_session_service's test fake)."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self._etag_counter = 0

    def _next_etag(self) -> str:
        self._etag_counter += 1
        return f"etag-{self._etag_counter}"

    def read_item(self, item, partition_key):  # noqa: ARG002
        if item not in self.items:
            raise CosmosResourceNotFoundError
        return self.items[item]

    def upsert_item(self, body):
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[body["id"]] = body
        return body

    def replace_item(self, item, body, etag=None, match_condition=None):
        from azure.core import MatchConditions
        from azure.cosmos.exceptions import CosmosAccessConditionFailedError

        current = self.items.get(item)
        if match_condition == MatchConditions.IfNotModified and current is not None and current.get("_etag") != etag:
            raise CosmosAccessConditionFailedError
        body = dict(body)
        body["_etag"] = self._next_etag()
        self.items[item] = body
        return body


class _EtagCosmosService:
    def __init__(self) -> None:
        self._containers: dict[str, _EtagContainer] = {}

    def get_container(self, name: str) -> _EtagContainer:
        return self._containers.setdefault(name, _EtagContainer())

    def query(self, container_name, sql, params=None, partition_key=None):  # noqa: ARG002
        return list(self.get_container(container_name).items.values())


def _configuration(**overrides):
    from backend.models.story import CharacterType, CompletionCriteria
    from backend.services.story_config_file import StoryConfiguration

    defaults = dict(
        worldPrompt="A flooded library beneath a coastal town.",
        characterTypes=[CharacterType(name="Archivist")],
        completionCriteria=CompletionCriteria(successConditions=["Recover the ledger"]),
        name="The Sunken Library",
    )
    defaults.update(overrides)
    return StoryConfiguration(**defaults)


def _derived(narrative_guidance="New guidance.", starting_point=None, admin_edited=None) -> DerivedContent:
    return DerivedContent(
        narrativeGuidance=narrative_guidance,
        startingPoint=starting_point or _starting_point(),
        adminEditedFields=admin_edited or [],
    )


def _generating_llm() -> MagicMock:
    llm = MagicMock()
    llm.generate_story_config.return_value = {"narrativeGuidance": "Fresh guidance."}
    llm.generate_starting_point.return_value = _starting_point(narrativeText="A fresh opening.").to_dict()
    return llm


def _service_with_etag(story: Story):
    cosmos = _EtagCosmosService()
    cosmos.get_container("stories").upsert_item(story.to_dict())
    llm = _generating_llm()
    service = StoryService(cosmos_service=cosmos, llm_service=llm)
    return service, cosmos, llm


def test_apply_content_write_preserves_identity_and_publish_fields_and_stamps_audit():
    story = _story(
        id="story-1",
        published=True,
        lastPublishedAt="2026-08-30T09:00:00Z",
        createdBy="creator-oid",
        createdAt="2026-08-01T00:00:00Z",
        contentUpdatedAt="2026-08-01T00:00:00Z",
        contentVersion=1,
        lastTestPlayedAt="2026-08-30T09:00:00Z",
    )
    service, _cosmos, _llm = _service_with_etag(story)
    configuration = _configuration(name="Renamed")

    updated = service.apply_content_write(story, configuration, "admin-oid", _derived("New guidance."))

    assert updated.id == story.id
    assert updated.createdBy == "creator-oid"
    assert updated.createdAt == "2026-08-01T00:00:00Z"
    assert updated.published is True
    assert updated.lastPublishedAt == "2026-08-30T09:00:00Z"
    assert updated.name == "Renamed"
    assert updated.narrativeGuidance == "New guidance."
    assert updated.lastUpdatedBy == "admin-oid"
    assert updated.contentVersion == 2
    assert updated.contentUpdatedAt != "2026-08-01T00:00:00Z"


def test_apply_content_write_regresses_can_publish_for_a_published_story():
    story = _story(
        published=True,
        contentUpdatedAt="2026-08-30T09:00:00Z",
        lastTestPlayedAt="2026-08-30T09:00:00Z",
    )
    service, _cosmos, _llm = _service_with_etag(story)

    updated = service.apply_content_write(story, _configuration(), "admin-oid", _derived("New guidance."))

    assert updated.published is True
    assert service.can_publish(updated) is False


def test_apply_content_write_retries_when_only_publish_changed_concurrently():
    story = _story(id="story-1", contentVersion=3)
    service, cosmos, _llm = _service_with_etag(story)

    # Simulate a concurrent publish landing between read and write: same contentVersion,
    # different _etag, published flipped.
    concurrent = _story(id="story-1", contentVersion=3, published=True, lastPublishedAt="2026-08-30T09:05:00Z")
    cosmos.get_container("stories").upsert_item(concurrent.to_dict())

    updated = service.apply_content_write(story, _configuration(), "admin-oid", _derived("New guidance."))

    assert updated.published is True
    assert updated.lastPublishedAt == "2026-08-30T09:05:00Z"
    assert updated.contentVersion == 4


def test_apply_content_write_raises_stale_story_when_content_version_changed():
    story = _story(id="story-1", contentVersion=3)
    service, cosmos, _llm = _service_with_etag(story)

    concurrent = _story(id="story-1", contentVersion=4)
    cosmos.get_container("stories").upsert_item(concurrent.to_dict())

    with pytest.raises(StaleStoryError):
        service.apply_content_write(story, _configuration(), "admin-oid", _derived("New guidance."))

    # Nothing was written for the rejected attempt.
    assert cosmos.get_container("stories").items["story-1"]["contentVersion"] == 4


def test_apply_content_write_is_exempt_from_staleness_for_import():
    story = _story(id="story-1", contentVersion=3)
    service, cosmos, _llm = _service_with_etag(story)

    concurrent = _story(id="story-1", contentVersion=4)
    cosmos.get_container("stories").upsert_item(concurrent.to_dict())

    updated = service.apply_content_write(
        story, _configuration(), "admin-oid", _derived("New guidance."), exempt_from_staleness=True
    )

    assert updated.contentVersion == 5


def test_apply_content_write_raises_write_conflict_after_a_second_precondition_failure():
    from azure.cosmos.exceptions import CosmosAccessConditionFailedError

    story = _story(id="story-1")
    service, cosmos, _llm = _service_with_etag(story)
    container = cosmos.get_container("stories")
    container.replace_item = MagicMock(side_effect=CosmosAccessConditionFailedError)

    with pytest.raises(WriteConflictError):
        service.apply_content_write(story, _configuration(), "admin-oid", _derived("New guidance."))


def test_import_configuration_creates_new_unpublished_story_when_id_absent():
    cosmos = _EtagCosmosService()
    service = StoryService(cosmos_service=cosmos, llm_service=_generating_llm())

    outcome, story = service.import_configuration(
        _configuration(), admin_oid="admin-oid", confirm_overwrite_story_id=None, title="A New Tale"
    )

    assert outcome == "created"
    assert story.published is False
    assert story.name == "A New Tale"
    assert story.contentVersion == 1
    assert story.lastUpdatedBy is None


def test_import_configuration_requires_title_when_id_absent():
    cosmos = _EtagCosmosService()
    service = StoryService(cosmos_service=cosmos, llm_service=MagicMock())

    with pytest.raises(TitleRequiredError):
        service.import_configuration(_configuration(), admin_oid="admin-oid", confirm_overwrite_story_id=None, title=None)


def test_import_configuration_overwrites_when_id_matches_and_confirmed():
    story = _story(id="story-1", contentVersion=2)
    service, cosmos, llm = _service_with_etag(story)

    outcome, updated = service.import_configuration(
        _configuration(id="story-1"), admin_oid="admin-oid", confirm_overwrite_story_id="story-1", title=None
    )

    assert outcome == "updated"
    assert updated.contentVersion == 3
    assert updated.published == story.published


def test_import_configuration_requires_confirmation_matching_the_id():
    story = _story(id="story-1")
    service, _cosmos, _llm = _service_with_etag(story)

    with pytest.raises(ConfirmationRequiredError):
        service.import_configuration(
            _configuration(id="story-1"), admin_oid="admin-oid", confirm_overwrite_story_id=None, title=None
        )


def test_import_configuration_raises_story_not_found_for_unmatched_id():
    cosmos = _EtagCosmosService()
    service = StoryService(cosmos_service=cosmos, llm_service=MagicMock())

    with pytest.raises(StoryNotFoundError):
        service.import_configuration(
            _configuration(id="missing"), admin_oid="admin-oid", confirm_overwrite_story_id="missing", title=None
        )


# --- delete_story (025-story-delete FR-003, FR-013) ---


def test_delete_story_removes_existing_story():
    story = _story(id="story-1")
    cosmos = MagicMock()
    cosmos.get_container.return_value.read_item.return_value = story.to_dict()
    service = StoryService(cosmos_service=cosmos)

    result = service.delete_story(story.id)

    assert result is True
    service._container().delete_item.assert_called_once_with(item=story.id, partition_key=story.id)


def test_delete_story_returns_false_for_nonexistent_story():
    cosmos = MagicMock()
    cosmos.get_container.return_value.delete_item.side_effect = CosmosResourceNotFoundError
    service = StoryService(cosmos_service=cosmos)

    assert service.delete_story("missing") is False


def test_delete_story_succeeds_regardless_of_published_state_true():
    story = _story(id="story-1", published=True)
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    assert service.delete_story(story.id) is True


def test_delete_story_succeeds_regardless_of_published_state_false():
    story = _story(id="story-1", published=False)
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)

    assert service.delete_story(story.id) is True


def test_deleting_an_already_deleted_story_returns_false():
    cosmos = MagicMock()
    service = StoryService(cosmos_service=cosmos)
    cosmos.get_container.return_value.delete_item.side_effect = CosmosResourceNotFoundError

    assert service.delete_story("story-1") is False


# --- Derived content: narrativeGuidance + startingPoint (#270, #271) ---


def test_derived_content_generates_both_when_the_configuration_supplies_neither():
    llm = _generating_llm()
    service = StoryService(cosmos_service=_EtagCosmosService(), llm_service=llm)

    derived = service.derived_content(_configuration(), "The Sunken Library")

    assert derived.narrativeGuidance == "Fresh guidance."
    assert derived.startingPoint.narrativeText == "A fresh opening."
    assert derived.adminEditedFields == []
    # The opening scene is anchored to the guidance generated alongside it.
    assert llm.generate_starting_point.call_args[0][1] == "Fresh guidance."


def test_derived_content_keeps_admin_authored_guidance_and_starting_point_verbatim():
    """Both are authored, editable content in the configuration file — a value the file
    carries is never overwritten by a regeneration (#270, #271)."""
    llm = _generating_llm()
    service = StoryService(cosmos_service=_EtagCosmosService(), llm_service=llm)
    configuration = _configuration(
        narrativeGuidance="Hand-edited guidance.",
        startingPoint=_starting_point(narrativeText="Hand-edited opening."),
    )

    derived = service.derived_content(configuration, "The Sunken Library")

    assert derived.narrativeGuidance == "Hand-edited guidance."
    assert derived.startingPoint.narrativeText == "Hand-edited opening."
    assert derived.adminEditedFields == ["narrativeGuidance", "startingPoint"]
    llm.generate_story_config.assert_not_called()
    llm.generate_starting_point.assert_not_called()


def test_derived_content_generates_an_opening_scene_for_hand_written_guidance():
    llm = _generating_llm()
    service = StoryService(cosmos_service=_EtagCosmosService(), llm_service=llm)

    derived = service.derived_content(
        _configuration(narrativeGuidance="Hand-edited guidance."), "The Sunken Library"
    )

    assert derived.startingPoint.narrativeText == "A fresh opening."
    assert derived.adminEditedFields == ["narrativeGuidance"]
    assert llm.generate_starting_point.call_args[0][1] == "Hand-edited guidance."


# --- ensure_starting_point: backfill for pre-#271 rows ---


def test_ensure_starting_point_returns_a_story_that_already_has_one_untouched():
    story = _story(startingPoint=_starting_point(narrativeText="The persisted opening."))
    service, _cosmos, llm = _service_with_etag(story)

    assert service.ensure_starting_point(story).startingPoint.narrativeText == "The persisted opening."
    llm.generate_starting_point.assert_not_called()


def test_ensure_starting_point_generates_and_persists_one_for_a_legacy_story():
    story = _story(id="story-1", startingPoint=None)
    service, cosmos, llm = _service_with_etag(story)

    updated = service.ensure_starting_point(story)

    assert updated.startingPoint.narrativeText == "A fresh opening."
    stored = cosmos.get_container("stories").items["story-1"]
    assert stored["startingPoint"]["narrativeText"] == "A fresh opening."
    # Generated from the story's own already-persisted guidance, not a fresh one.
    llm.generate_story_config.assert_not_called()
    assert llm.generate_starting_point.call_args[0][1] == story.narrativeGuidance


def test_ensure_starting_point_yields_to_a_backfill_that_landed_first():
    story = _story(id="story-1", startingPoint=None)
    service, cosmos, llm = _service_with_etag(story)
    winner = _story(id="story-1", startingPoint=_starting_point(narrativeText="The winning opening."))
    cosmos.get_container("stories").upsert_item(winner.to_dict())

    updated = service.ensure_starting_point(story)

    assert updated.startingPoint.narrativeText == "The winning opening."
    assert cosmos.get_container("stories").items["story-1"]["startingPoint"]["narrativeText"] == "The winning opening."


def test_ensure_starting_point_still_returns_an_opening_when_the_write_loses_its_race():
    from azure.cosmos.exceptions import CosmosAccessConditionFailedError

    story = _story(id="story-1", startingPoint=None)
    service, cosmos, _llm = _service_with_etag(story)
    cosmos.get_container("stories").replace_item = MagicMock(side_effect=CosmosAccessConditionFailedError)

    assert service.ensure_starting_point(story).startingPoint.narrativeText == "A fresh opening."


def test_ensure_starting_point_raises_not_found_for_a_deleted_story():
    story = _story(id="story-1", startingPoint=None)
    service, cosmos, _llm = _service_with_etag(story)
    del cosmos.get_container("stories").items["story-1"]

    with pytest.raises(StoryNotFoundError):
        service.ensure_starting_point(story)


# --- Hand-edited derived content survives a later write (user review, PR #279) ---


def test_derived_content_marks_a_supplied_value_that_differs_as_hand_edited():
    story = _story(narrativeGuidance="Generated guidance.")
    service, _cosmos, _llm = _service_with_etag(story)

    derived = service.derived_content(
        _configuration(id="story-1", narrativeGuidance="Hand-edited guidance."), "The Sunken Library", existing=story
    )

    assert derived.adminEditedFields == ["narrativeGuidance"]


def test_derived_content_does_not_mark_an_untouched_round_trip_of_a_generated_value():
    """Downloading and re-uploading a file without touching it must not freeze the
    generated guidance — nothing was hand-edited."""
    story = _story(narrativeGuidance="Generated guidance.", startingPoint=_starting_point())
    service, _cosmos, _llm = _service_with_etag(story)

    derived = service.derived_content(
        _configuration(
            id="story-1", narrativeGuidance="Generated guidance.", startingPoint=_starting_point()
        ),
        "The Sunken Library",
        existing=story,
    )

    assert derived.adminEditedFields == []


def test_derived_content_keeps_the_hand_edited_mark_when_the_same_value_is_resubmitted():
    story = _story(narrativeGuidance="Hand-edited guidance.", adminEditedFields=["narrativeGuidance"])
    service, _cosmos, _llm = _service_with_etag(story)

    derived = service.derived_content(
        _configuration(id="story-1", narrativeGuidance="Hand-edited guidance."), "The Sunken Library", existing=story
    )

    assert derived.adminEditedFields == ["narrativeGuidance"]


def test_derived_content_clears_the_hand_edited_mark_when_the_file_omits_the_field():
    """Deleting the key from the file is how an administrator asks for a fresh
    generation, so it also gives ownership of the field back to the system."""
    story = _story(narrativeGuidance="Hand-edited guidance.", adminEditedFields=["narrativeGuidance"])
    service, _cosmos, _llm = _service_with_etag(story)

    derived = service.derived_content(_configuration(id="story-1"), "The Sunken Library", existing=story)

    assert derived.narrativeGuidance == "Fresh guidance."
    assert derived.adminEditedFields == []


def test_carry_admin_edits_seeds_only_the_hand_edited_fields():
    story = _story(
        narrativeGuidance="Hand-edited guidance.",
        startingPoint=_starting_point(narrativeText="Generated opening."),
        adminEditedFields=["narrativeGuidance"],
    )
    service, _cosmos, _llm = _service_with_etag(story)
    configuration = _configuration()

    service.carry_admin_edits(story, configuration)

    assert configuration.narrativeGuidance == "Hand-edited guidance."
    assert configuration.startingPoint is None


def test_apply_content_write_persists_which_fields_were_hand_edited():
    story = _story(id="story-1")
    service, cosmos, _llm = _service_with_etag(story)

    updated = service.apply_content_write(
        story, _configuration(), "admin-oid", _derived(admin_edited=["startingPoint"])
    )

    assert updated.adminEditedFields == ["startingPoint"]
    assert cosmos.get_container("stories").items["story-1"]["adminEditedFields"] == ["startingPoint"]
