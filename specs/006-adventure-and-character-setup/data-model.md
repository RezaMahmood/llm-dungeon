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
| `characterTypes` | `list[CharacterType]` | The set a player chooses one `name` from (FR-003) |
| `tone` | `Optional[str]` | List card kicker, per `02-story-story-select.html` design reference |
| `readingLevel` | `Optional[str]` | List card meta text ("Reading level: X") |
| `sessionLengthMinutes` | `Optional[int]` | List card kicker (tone · minutes) |

No field on `Story` is created, updated, or deleted by this feature — it is strictly a
read path.

### CharacterType (`src/backend/models/story.py`)

| Field | Type | Used for |
|---|---|---|
| `name` | `str` | The value a player selects and submits as `characterType` (FR-003) |
| `description` | `Optional[str]` | Shown to help the player choose between types |

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
| `characterTypes` | `array<{ name: string, description: string \| null }>` | The set shown in step 3 (FR-003) |

Only returned for a published story (unpublished adventures are never player-visible, FR-001);
requesting an unpublished or nonexistent id returns 404, same as any other not-found case.

### PlaySetupRequest (request body of `POST /api/game/start`)

| Field | Type | Validation |
|---|---|---|
| `adventureId` | `string` | Required. Must reference an existing, published `Story` (FR-001). |
| `characterName` | `string` | Required. Non-blank after trim; ≤50 characters (FR-002). |
| `characterType` | `string` | Required. Must equal a `name` in the selected story's `characterTypes` (FR-003). |

### PlaySetupResponse (success response of `POST /api/game/start`)

| Field | Type | Notes |
|---|---|---|
| `status` | `"success"` | |
| `adventureId` | `string` | Echoed back |
| `characterName` | `string` | Echoed back (trimmed) |
| `characterType` | `string` | Echoed back |

Confirms setup is complete and valid; does not itself represent a play session (Decision 4 —
session creation is `008-core-gameplay`'s responsibility).

## Validation Rules Summary (server-side, Constitution Principle II)

- FR-001/FR-006: `GET /api/game/adventures` returns only `published == true` stories; when none
  qualify, an empty array (frontend renders the "nothing available yet" message, not the API).
- FR-002: `characterName` — reject empty/whitespace-only and length > 50 with a field-identified
  error (FR-005).
- FR-003: `characterType` — reject any value not present in the selected adventure's
  `characterTypes` names, with a field-identified error.
- FR-003a/FR-004: `POST /api/game/start` independently validates all three fields every call —
  there is no server-side "step" state to trust; a request missing or failing any one field is
  rejected and MUST identify which field(s) are the problem (FR-005).
- FR-004a: Purely client-side (Decision 6) — no server validation rule corresponds to this FR.

## State Transitions

None — no entity in this feature has a lifecycle/state machine. `Story.published` is owned and
transitioned by `005-story-publishing`, read-only here.
