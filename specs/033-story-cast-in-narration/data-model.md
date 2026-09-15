# Data Model: The Story's Cast Reaches the Narration

No entity's stored shape changes in this slice (Assumption: "the roster's stored shape does not
change"). This documents the one entity involved and its new use, per FR-001/FR-002/FR-004.

## Character Archetype (existing — `CharacterType`)

Defined at `src/backend/models/story.py:18-32`, stored as `Story.characterTypes: list[CharacterType]`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | `str` | Yes | Validated non-empty in `__post_init__`; unique case-insensitively per story (`story_config_file.py`) |
| `description` | `Optional[str]` | No | Currently persisted and validated but never read by the narration prompt — this slice is what starts using it |

**Validation (unchanged)**:
- `Story.__post_init__` (`story.py:183-184`) requires `characterTypes` to have at least one entry.
- `story_config_file.py` (`_parse_character_types`, line 195) rejects an empty list, a non-object
  entry missing `name`, and case-insensitive duplicate names on upload.

**New use, no new field**: `_build_gameplay_turn_prompt` (`llm_service.py`) reads
`story.characterTypes` (already in scope) to render a cast block distinct from the existing
`Character: {name} ({type})` player line. An entry with no `description` still renders by name
alone (Edge Case: "a roster entry has a name but no description").

## Relationship to the player's own character

`PlaySession.characterName` / `characterType` (`play_session_service.py:172,194-228`) continue to
echo the player's chosen roster entry, unchanged (FR-005). The cast block includes that same
entry among the story's cast (Edge Case: "the player's own chosen character type is also a roster
entry... must not treat the player as two characters") — the narration is not told to exclude it,
since the spec requires no change to which entries are supplied, only that the player's own line
stays distinct from the cast listing.

## No new entities

This slice defines no new persisted entity, request/response shape, or configuration field.
