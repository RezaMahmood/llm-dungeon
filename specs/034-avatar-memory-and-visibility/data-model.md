# Data Model: Remembering and Showing a Player's Avatar

## `StoredAvatarDescription` (new)

One document per `(playerId, storyId)` pair, in a new container
(`config.STORED_AVATAR_DESCRIPTIONS_CONTAINER = "storedAvatarDescriptions"`), partitioned and keyed
by `id = f"{playerId}:{storyId}"` — mirrors `AvatarSetupAttempts`'s exact key convention (`032`).

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | `f"{playerId}:{storyId}"`. |
| `playerId` | `str` | The player who wrote it; never disclosed to another player or an administrator (FR-011). |
| `storyId` | `str` | The adventure it was written for. |
| `description` | `str` | The most recent validated avatar description this player used for this adventure (FR-005). Re-validated on submission, never trusted because it passed before (FR-008) — this document stores it as-is, with no re-validation at storage time (spec.md Assumptions). |
| `updatedAt` | `str` | ISO-8601 UTC timestamp of the write, for debugging/observability only — no requirement reads it. |
| `entityType` | `str` | `"StoredAvatarDescription"`, matching this codebase's existing per-entity discriminator convention. |

Upserted (read-modify-write against the document's Cosmos `_etag`, same bounded-retry shape as
`AvatarSetupAttemptsService.record_attempt`) whenever `PlaySessionService.create_session` succeeds
— replacing, never accumulating (FR-005, Out of Scope: no library of saved characters). Deleted in
bulk when the adventure it belongs to is deleted (FR-009); untouched by any session-delete path
(FR-010). No TTL — this codebase uses none anywhere; the document is exactly as long-lived as the
adventure it belongs to.

## `PlaySession` (existing — `models/play_session.py:78`)

No field or shape change. `avatarDescription` already exists (`032`); this slice only adds it to
one more read path, `get_session_detail_for_player`'s response shape, which is a service-method
behavior change, not a `PlaySession` field change.

## `Story` / `Story.totalTokens` (existing — `models/story.py:177`)

No field or writer change. FR-009a is a negative constraint on the *deletion* path introduced by
this slice: `StoredAvatarDescriptionService.delete_for_story` and `create_session`'s upsert must
never call any `Story.totalTokens`-mutating method. Documented here because it is a constraint on
a field this slice's new code runs near, not because the field itself changes.

## Response-shape additions (no `contracts/` — see plan.md)

- `GET /game/adventures/{adventureId}` → `adventure.avatarDescription: str | null` — the caller's
  own stored description for this adventure, or `null` if none exists (FR-006, FR-007).
- `GET /game/sessions/{sessionId}` → `session.avatarDescription: str | null` — the session's own
  description, already on `PlaySession` (FR-001, FR-003).

## Relationship summary

- **Setup, returning player**: `GET /game/adventures/{id}` returns a non-null
  `avatarDescription`; the field prefills but remains fully editable (FR-006). Starting
  unchanged, edited, or replaced all validate identically (FR-008) and all overwrite the stored
  document on success (Decision 2).
- **Setup, first-time player for this adventure**: `avatarDescription` is `null`; the field starts
  empty (FR-007).
- **Mid-session**: the status panel reads the session's own `avatarDescription`
  (`get_session_detail_for_player`), independent of whatever is currently stored for
  `(playerId, storyId)` — the two can only differ if the player later starts a *new* session with
  an edited description while an older, concluded session with the original text still exists.
- **Adventure deleted**: every `StoredAvatarDescription` row for that `storyId` is deleted
  (FR-009); any `PlaySession.avatarDescription` values already written are untouched (they belong
  to sessions, which the existing `025` cascade handles separately).
- **A session deleted**: no `StoredAvatarDescription` row is touched (FR-010).
