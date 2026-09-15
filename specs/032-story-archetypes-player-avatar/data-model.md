# Data Model: A Player-Authored Avatar Replaces the Character-Type Picker

## `PlaySession` (existing — `models/play_session.py:78`)

| Field | Type | Change |
|---|---|---|
| `characterName` | `str` | Unchanged (FR-003, FR-005, FR-027). |
| `characterType` | `str` → `Optional[str] = None` | Widened for backward compatibility only. Never set on a new session (FR-002, FR-022). A pre-existing document keeps whatever value it already has; it is never read as the player's identity again (FR-026). |
| `avatarDescription` | **new** `Optional[str] = None` | The player's free-text description (20–500 chars, validated — FR-001, FR-006–FR-008). Set once at session creation, fixed for the session's life (FR-020). `None` on a session resumed from before this change (FR-026–FR-027). |

`to_dict()`/`from_dict()` both updated: `characterType` read via `data.get("characterType")`,
`avatarDescription` via `data.get("avatarDescription")`. No other field changes. Mirrors the same
change on `TestPlaySession` (`models/test_play_session.py`), except a `TestPlaySession` always sets
`avatarDescription` to the fixed tester constant and never sets `characterType` at all (Decision 6).

## `AvatarSetupAttempts` (new)

One document per `(playerId, storyId)` pair, in a new container (`config.AVATAR_SETUP_ATTEMPTS_CONTAINER
= "avatarSetupAttempts"`), partitioned and keyed by `id = f"{playerId}:{storyId}"`.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | `f"{playerId}:{storyId}"`. |
| `playerId` | `str` | |
| `storyId` | `str` | |
| `modelBackedAttempts` | `int` | Incremented immediately before each model-backed relevance check (FR-010, FR-014); cost-free rejections never touch this. |
| `entityType` | `str` | `"AvatarSetupAttempts"`, matching this codebase's existing per-entity discriminator convention. |

Deleted once a session is successfully created for that `(playerId, storyId)` pair, so a later,
separate setup against the same adventure starts fresh. No TTL (this codebase uses none anywhere;
a stale document is a bounded, harmless leftover — Assumption: "a guard rail, not a quota").
Read-modify-write against the document's Cosmos `_etag`, same bounded-retry shape as
`PlayerContentSafetyStandingService` and every `Story.totalTokens` writer in `story_service.py`.

## `Story` / `Story.totalTokens` (existing — `models/story.py:177`)

No field change. A new `StoryService` method accrues a validation call's tokens into the existing
`totalTokens` field via the same guarded read-modify-write `record_test_play` already uses
(Decision 4) — documented here because it is a new *writer* of an existing field, not a new field.

## `CharacterType` (existing — unchanged, `033-story-cast-in-narration`'s data-model.md still
applies)

No shape or validation change. After this slice it is authored and read only as story-world cast
material (`033`); it is never read as a player-selectable option anywhere (FR-022, FR-023).

## Relationship summary

- A **new** session: `characterType=None`, `avatarDescription=<validated player text>`.
- A **pre-existing, resumed** session: `characterType=<old value, unused>`,
  `avatarDescription=None`; the narration falls back to the character name alone (Decision 5).
- A **test-play** session: `characterType=None`, `avatarDescription=<fixed tester constant>`.
