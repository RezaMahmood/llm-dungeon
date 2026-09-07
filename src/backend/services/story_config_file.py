"""The Story Configuration File — one canonical serializer and validator feeding the
read-only viewer, the download, and the import endpoint (data-model.md → StoryConfiguration;
contracts/api.md; research.md §2, §7). `serialize` and `parse`/`parse_text` are the only
places this feature reads or writes the file's bytes; nothing else may re-serialize a Story
or re-implement these rules (research.md §1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.models.story import VALID_RULES, CharacterType, CompletionCriteria, Story

# Accepted-and-ignored on upload, never emitted on download (data-model.md → Excluded keys).
# These are the Story fields this feature does not treat as authored content.
SYSTEM_MANAGED_KEYS = {
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
}

# Every key this feature ever emits or accepts, in the exact order serialize() emits them
# (minus `id`, which is conditional and always first — data-model.md → Serialization contract).
_AUTHORED_KEYS_IN_ORDER = (
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
)

_KNOWN_KEYS = {"id", *_AUTHORED_KEYS_IN_ORDER, *SYSTEM_MANAGED_KEYS}


class InvalidStoryConfigurationError(ValueError):
    """The uploaded/parsed configuration failed a file-level or content rule — the caller
    maps this to `422 invalid_configuration` with `str(exc)` naming the offending field or
    element (contracts/api.md)."""


@dataclass
class StoryConfiguration:
    """The parsed, validated, transient form of a Story Configuration File — never
    persisted (data-model.md → StoryConfiguration)."""

    worldPrompt: str
    characterTypes: list[CharacterType]
    completionCriteria: CompletionCriteria
    id: Optional[str] = None
    name: Optional[str] = None
    coverImageUrl: Optional[str] = None
    tone: Optional[str] = None
    readingLevel: Optional[str] = None
    sessionLengthMinutes: Optional[int] = None
    chapters: Optional[int] = None
    rules: Optional[str] = None


def serialize(story: Story) -> str:
    """The canonical bytes: fixed key order, 2-space indent, `ensure_ascii=False`, one
    trailing newline. `id` is emitted first (data-model.md → Serialization contract)."""
    payload: dict[str, Any] = {"id": story.id}
    payload["name"] = story.name
    payload["coverImageUrl"] = story.coverImageUrl
    payload["tone"] = story.tone
    payload["readingLevel"] = story.readingLevel
    payload["sessionLengthMinutes"] = story.sessionLengthMinutes
    payload["chapters"] = story.chapters
    payload["worldPrompt"] = story.worldPrompt
    payload["rules"] = story.rules
    payload["characterTypes"] = [ct.to_dict() for ct in story.characterTypes]
    payload["completionCriteria"] = story.completionCriteria.to_dict()
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def parse_text(text: str) -> StoryConfiguration:
    """Turn raw uploaded text into a validated `StoryConfiguration`. A JSON decode failure
    becomes an `InvalidStoryConfigurationError` naming the parser's position (research.md
    §7); this makes malformed JSON a server-side rejection, not only a client-side one."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidStoryConfigurationError(
            f"The file is not valid JSON (line {exc.lineno}, column {exc.colno})"
        ) from exc
    return parse(payload)


def parse(payload: Any) -> StoryConfiguration:
    """Validate a decoded payload against every StoryConfiguration rule (data-model.md,
    research.md §7). Raises `InvalidStoryConfigurationError` naming the offending field on
    the first failure; nothing is partially accepted."""
    if not isinstance(payload, dict):
        raise InvalidStoryConfigurationError("The file must contain a JSON object")

    unknown_keys = set(payload.keys()) - _KNOWN_KEYS
    if unknown_keys:
        first = sorted(unknown_keys)[0]
        raise InvalidStoryConfigurationError(f"{first}: unrecognised field")

    story_id = payload.get("id") or None
    name = payload.get("name") or None
    if story_id and not name:
        raise InvalidStoryConfigurationError("name: a name is required when overwriting an existing story")

    world_prompt = payload.get("worldPrompt")
    if not world_prompt:
        raise InvalidStoryConfigurationError("worldPrompt: a world prompt is required")

    raw_character_types = payload.get("characterTypes")
    if not raw_character_types:
        raise InvalidStoryConfigurationError("characterTypes: at least one character type is required")
    character_types = _parse_character_types(raw_character_types)

    raw_completion_criteria = payload.get("completionCriteria")
    if not raw_completion_criteria:
        raise InvalidStoryConfigurationError("completionCriteria: completion criteria are required")
    completion_criteria = _parse_completion_criteria(raw_completion_criteria)

    for int_field in ("sessionLengthMinutes", "chapters"):
        value = payload.get(int_field)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            raise InvalidStoryConfigurationError(f"{int_field}: must be a positive integer")

    return StoryConfiguration(
        id=story_id,
        name=name,
        coverImageUrl=payload.get("coverImageUrl"),
        tone=payload.get("tone"),
        readingLevel=payload.get("readingLevel"),
        sessionLengthMinutes=payload.get("sessionLengthMinutes"),
        chapters=payload.get("chapters"),
        worldPrompt=world_prompt,
        rules=payload.get("rules"),
        characterTypes=character_types,
        completionCriteria=completion_criteria,
    )


def _parse_character_types(raw: Any) -> list[CharacterType]:
    if not isinstance(raw, list):
        raise InvalidStoryConfigurationError("characterTypes: at least one character type is required")
    character_types: list[CharacterType] = []
    seen_names: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise InvalidStoryConfigurationError("characterTypes: each character type must be an object with a name")
        try:
            ct = CharacterType.from_dict(entry)
        except (ValueError, KeyError) as exc:
            raise InvalidStoryConfigurationError(f"characterTypes: {exc}") from exc
        key = ct.name.strip().lower()
        if key in seen_names:
            raise InvalidStoryConfigurationError(f"characterTypes: duplicate character type name {ct.name!r}")
        seen_names.add(key)
        character_types.append(ct)
    return character_types


def _parse_completion_criteria(raw: Any) -> CompletionCriteria:
    if not isinstance(raw, dict):
        raise InvalidStoryConfigurationError("completionCriteria: completion criteria are required")
    if not raw.get("successConditions"):
        raise InvalidStoryConfigurationError("completionCriteria.successConditions: at least one success condition is required")
    total_conditions = len(raw.get("successConditions") or []) + len(raw.get("failureConditions") or [])
    rule = raw.get("rule")
    if total_conditions > 1 and (not rule or rule not in VALID_RULES):
        raise InvalidStoryConfigurationError(
            "completionCriteria.rule: rule is required and must be one of "
            f"{sorted(VALID_RULES)} when more than one condition is defined"
        )
    try:
        return CompletionCriteria.from_dict(raw)
    except (ValueError, KeyError) as exc:
        raise InvalidStoryConfigurationError(f"completionCriteria: {exc}") from exc
