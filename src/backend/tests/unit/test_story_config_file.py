"""Unit tests for story_config_file: exact serialization bytes, excluded fields, and every
validation rejection reason (data-model.md → StoryConfiguration; contracts/api.md;
quickstart.md scenarios 4, 12)."""

from __future__ import annotations

import json

import pytest

from backend.services.story_config_file import (
    InvalidStoryConfigurationError,
    parse,
    parse_text,
    serialize,
)


# --- Serialization exactness (FR-002, FR-004, SC-001) ---


def test_serialize_emits_fixed_key_order_with_id_first(_story):
    story = _story(id="story-1", name="The Sunken Library")

    text = serialize(story)

    keys = list(json.loads(text).keys())
    assert keys == [
        "id",
        "name",
        "coverImageUrl",
        "tone",
        "readingLevel",
        "sessionLengthMinutes",
        "chapters",
        "worldPrompt",
        "rules",
        "characterTypes",
        "completionCriteria",
    ]


def test_serialize_uses_two_space_indent_and_trailing_newline(_story):
    story = _story()

    text = serialize(story)

    assert text.endswith("\n")
    assert not text.endswith("\n\n")
    assert '{\n  "id"' in text


def test_serialize_excludes_every_system_managed_field(_story):
    story = _story(
        published=True,
        lastPublishedAt="2026-08-30T00:00:00Z",
        createdBy="admin-oid",
        createdAt="2026-08-30T00:00:00Z",
        contentUpdatedAt="2026-08-30T00:00:00Z",
        lastUpdatedBy="admin-oid",
        lastTestPlayedAt="2026-08-30T00:00:00Z",
        contentVersion=3,
    )

    parsed = json.loads(serialize(story))

    for excluded in (
        "published",
        "lastPublishedAt",
        "createdBy",
        "createdAt",
        "contentUpdatedAt",
        "lastUpdatedBy",
        "lastTestPlayedAt",
        "contentVersion",
        "entityType",
        "narrativeGuidance",
    ):
        assert excluded not in parsed


# --- parse_text: malformed JSON is a server-side rejection (research.md §7) ---


def test_parse_text_rejects_malformed_json_naming_position():
    with pytest.raises(InvalidStoryConfigurationError, match=r"line \d+, column \d+"):
        parse_text("{ not valid json")


def test_parse_text_accepts_valid_json_and_parses_it():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["Recover the ledger"]},
    }
    config = parse_text(json.dumps(payload))
    assert config.worldPrompt == "A flooded library."


# --- parse: structural rules ---


def test_parse_rejects_non_object_payload():
    with pytest.raises(InvalidStoryConfigurationError, match="JSON object"):
        parse(["not", "an", "object"])


def test_parse_rejects_unrecognised_key():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["Recover the ledger"]},
        "notAField": "oops",
    }
    with pytest.raises(InvalidStoryConfigurationError, match="notAField"):
        parse(payload)


def test_parse_ignores_known_system_managed_keys():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["Recover the ledger"]},
        "published": True,
        "createdBy": "someone",
        "narrativeGuidance": "stale guidance",
    }
    config = parse(payload)
    assert config.worldPrompt == "A flooded library."


def test_parse_rejects_empty_world_prompt():
    payload = {
        "worldPrompt": "",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["Recover the ledger"]},
    }
    with pytest.raises(InvalidStoryConfigurationError, match="worldPrompt"):
        parse(payload)


def test_parse_rejects_missing_character_types():
    payload = {"worldPrompt": "A flooded library.", "completionCriteria": {"successConditions": ["x"]}}
    with pytest.raises(InvalidStoryConfigurationError, match="characterTypes"):
        parse(payload)


def test_parse_rejects_empty_character_types():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [],
        "completionCriteria": {"successConditions": ["x"]},
    }
    with pytest.raises(InvalidStoryConfigurationError, match="characterTypes"):
        parse(payload)


def test_parse_rejects_duplicate_character_type_names_case_insensitively():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}, {"name": "archivist"}],
        "completionCriteria": {"successConditions": ["x"]},
    }
    with pytest.raises(InvalidStoryConfigurationError, match="duplicate"):
        parse(payload)


def test_parse_rejects_missing_completion_criteria():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
    }
    with pytest.raises(InvalidStoryConfigurationError, match="completionCriteria"):
        parse(payload)


def test_parse_rejects_missing_success_conditions():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": []},
    }
    with pytest.raises(InvalidStoryConfigurationError, match="successConditions"):
        parse(payload)


def test_parse_rejects_rule_outside_any_all_with_multiple_conditions():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {
            "successConditions": ["Recover the ledger"],
            "failureConditions": ["The lamp goes out"],
            "rule": "maybe",
        },
    }
    with pytest.raises(InvalidStoryConfigurationError, match="rule"):
        parse(payload)


def test_parse_accepts_single_condition_with_no_rule():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["Recover the ledger"]},
    }
    config = parse(payload)
    assert config.completionCriteria.rule is None


@pytest.mark.parametrize("field_name", ["sessionLengthMinutes", "chapters"])
def test_parse_rejects_non_positive_integer_fields(field_name):
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["x"]},
        field_name: 0,
    }
    with pytest.raises(InvalidStoryConfigurationError, match=field_name):
        parse(payload)


def test_parse_rejects_missing_name_on_overwrite_path():
    payload = {
        "id": "story-1",
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["x"]},
    }
    with pytest.raises(InvalidStoryConfigurationError, match="name"):
        parse(payload)


def test_parse_rejects_empty_name_on_overwrite_path():
    payload = {
        "id": "story-1",
        "name": "",
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["x"]},
    }
    with pytest.raises(InvalidStoryConfigurationError, match="name"):
        parse(payload)


def test_parse_does_not_require_name_on_id_less_path():
    payload = {
        "worldPrompt": "A flooded library.",
        "characterTypes": [{"name": "Archivist"}],
        "completionCriteria": {"successConditions": ["x"]},
    }
    config = parse(payload)
    assert config.id is None
    assert config.name is None
