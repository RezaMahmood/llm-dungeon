# Phase 1 Data Model: Adventure and Character Setup

**Feature**: 006-adventure-and-character-setup | **Date**: 2026-08-31

No new persisted entity is introduced (see [research.md](./research.md) Decision 1). This
document describes the entities this feature *reads* (already defined in `004-story-creation-done`)
and the request/response shapes it introduces, which exist only for the lifetime of an HTTP
call — never persisted as-is.

## Existing entities reused (read-only)

### Story (`src/backend/models/story.py`)

Fields relevant to this feature:

| Field | Type | Used for |
|---|---|---|
| `id` | `str` | The `adventureId` a player selects (FR-001) |
| `name` | `Optional[str]` | Distinguishing adventures in the list (FR-001) |
| `published` | `bool` | Filters the player-facing list to published-only (FR-001, FR-006) |
| `characterTypes` | `list[CharacterType]` | The story's cast of characters, available to the narration as story-world material — never a set the player chooses from (`032-story-archetypes-player-avatar` FR-022, `033-story-cast-in-narration`) |
| `tone` | `Optional[str]` | List card kicker, per `02-story-story-select.html` design reference |
| `readingLevel` | `Optional[str]` | List card meta text ("Reading level: X") |
| `sessionLengthMinutes` | `Optional[int]` | List card kicker (tone · minutes) |

No field on `Story` is created, updated, or deleted by this feature — it is strictly a
read path.

### CharacterType (`src/backend/models/story.py`)

| Field | Type | Used for |
|---|---|---|
| `name` | `str` | Names one of the story's cast, for the narration's use (`033-story-cast-in-narration`) |
| `description` | `Optional[str]` | Optional detail about that cast member, for the narration's use |

## New non-persisted request/response shapes

These exist only as JSON payloads on the wire — never written to Cosmos as their own record.

### AdventureSummary (response element of `GET /api/game/adventures`)

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Story id — becomes the `adventureId` submitted to `POST /api/game/start` |
| `name` | `string` | Distinguishing label (FR-001) |
| `tone` | `string \| null` | Card kicker |
| `sessionLengthMinutes` | `number \| null` | Card kicker |
| `readingLevel` | `string \| null` | Card meta |

Only stories where `published == true` ever appear in this list (FR-001, FR-006). No
`characterTypes` field here — that detail is fetched only once an adventure is selected (see
below), keeping the list payload light.

### AdventureDetail (response of `GET /api/game/adventures/{adventureId}`, or an embedded
field — see contracts/api.md for the exact chosen shape)

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | |
| `name` | `string` | |
| `avatarDescription` | `string \| null` | The caller's own stored description for this adventure, prefilled at setup, or `null` if they have none (`034-avatar-memory-and-visibility` FR-006, FR-007) |

No `characterTypes` field: the story's cast is narration material the player never selects
from, so it is neither projected nor returned to a player-facing client
(`032-story-archetypes-player-avatar` FR-002, FR-022).

Only returned for a published story (unpublished adventures are never player-visible, FR-001);
requesting an unpublished or nonexistent id returns 404, same as any other not-found case.

### PlaySetupRequest (request body of `POST /api/game/start`)

| Field | Type | Validation |
|---|---|---|
| `adventureId` | `string` | Required. Must reference an existing, published `Story` (FR-001). |
| `characterName` | `string` | Required. Non-blank after trim; ≤50 characters (FR-002). |
| `avatarDescription` | `string` | Required. The player's own free-text description of their character, 20–500 characters after trimming, additionally validated for story-relevance and injection resistance (`032-story-archetypes-player-avatar` FR-001, FR-006–FR-008). Replaces the former `characterType` field, which is no longer accepted. |

### PlaySetupResponse (success response of `POST /api/game/start`)

| Field | Type | Notes |
|---|---|---|
| `status` | `"success"` | |
| `adventureId` | `string` | Echoed back |
| `characterName` | `string` | Echoed back (trimmed) |
| `avatarDescription` | `string` | Echoed back (trimmed) |

Confirms setup is complete and valid; does not itself represent a play session (Decision 4 —
session creation is `008-core-gameplay-done`'s responsibility).

## Validation Rules Summary (server-side, Constitution Principle II)

- FR-001/FR-006: `GET /api/game/adventures` returns only `published == true` stories; when none
  qualify, an empty array (frontend renders the "nothing available yet" message, not the API).
- FR-002: `characterName` — reject empty/whitespace-only and length > 50 with a field-identified
  error (FR-005).
- FR-003: `avatarDescription` — reject blank, and anything outside 20–500 characters after
  trimming, with a field-identified error and without any model call; then reject a description
  the story-relevance check judges not to be a character description, or on which it reaches no
  verdict (`032-story-archetypes-player-avatar` FR-006, FR-007, FR-010, FR-012). No value is
  validated against the adventure's `characterTypes`, which the player never selects from.
- FR-003a/FR-004: `POST /api/game/start` independently validates all three fields every call —
  there is no server-side "step" state to trust; a request missing or failing any one field is
  rejected and MUST identify which field(s) are the problem (FR-005).
- FR-004a: Purely client-side (Decision 6) — no server validation rule corresponds to this FR.

## State Transitions

None — no entity in this feature has a lifecycle/state machine. `Story.published` is owned and
transitioned by `005-story-publishing-done`, read-only here.
