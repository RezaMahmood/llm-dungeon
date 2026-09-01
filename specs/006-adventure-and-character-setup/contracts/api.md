# API Contracts: Adventure and Character Setup

**Date**: 2026-08-31

**Feature**: Adventure and Character Setup (006-adventure-and-character-setup)

Adds one new endpoint (`GET /api/game/adventures`) and extends one existing placeholder
endpoint (`POST /api/game/start`, `src/backend/api/game/start.py`). Both require an
authenticated Player (`authorize_player` — new, mirrors `authorize_admin`, see
[research.md](../research.md) Decision 3), returning the same `unauthorized()` /
`forbidden_access_not_granted()` / `forbidden_insufficient_permission()` shapes as existing
endpoints on failure (`src/backend/api/utils.py`). Response shapes follow the same
`json_response`/`error_response` helper conventions as `004-story-creation` and
`005-story-publishing`'s contracts.

---

## GET /api/game/adventures

**Purpose**: List published adventures a player can choose from (FR-001), for the first step
of setup. Player-scoped — no `published` filter is client-controllable; this endpoint always
and only returns `published == true` stories.

**Request**: No parameters, no body.

**Response (200 OK)**:
```json
{
  "status": "success",
  "adventures": [
    {
      "id": "9f2a...",
      "name": "Nine Doors of Mudlark Hall",
      "tone": "Mystery",
      "sessionLengthMinutes": 20,
      "readingLevel": "Year 5"
    }
  ]
}
```

An empty `adventures` array (`[]`) is a valid 200 response — it means no adventures are
currently published (FR-006); the frontend is responsible for rendering the "nothing available
yet" message in that case, not the API.

Character types are intentionally omitted from this list response (kept light); fetch them via
`GET /api/game/adventures/{adventureId}` once a player selects an adventure.

---

## GET /api/game/adventures/{adventureId}

**Purpose**: Fetch one published adventure's character types (FR-003), once selected in step 1.

**Request**: `adventureId` path parameter.

**Response (200 OK)**:
```json
{
  "status": "success",
  "adventure": {
    "id": "9f2a...",
    "name": "Nine Doors of Mudlark Hall",
    "characterTypes": [
      { "name": "Detective", "description": "Sharp-eyed and methodical." },
      { "name": "Ghost", "description": "Already knows every room — but not why." }
    ]
  }
}
```

**Response (404 Not Found)** — id does not exist, or exists but is not published (a player
must never learn an unpublished adventure exists, so both cases return the identical response):
```json
{ "error": "not_found", "message": "Adventure not found" }
```

---

## POST /api/game/start

**Purpose**: Validate a completed setup (adventure, character name, character type) and confirm
the player may proceed (FR-002, FR-003, FR-004, FR-005). Supersedes the current placeholder
body in `src/backend/api/game/start.py`. Does **not** create a play session — that remains
`008-core-gameplay`'s responsibility (see [research.md](../research.md) Decision 4); a 200
response here means "this setup is valid," not "a session now exists."

**Request**:
```json
{
  "adventureId": "9f2a...",
  "characterName": "Wren",
  "characterType": "Detective"
}
```

**Response (200 OK)** — all three fields valid:
```json
{
  "status": "success",
  "adventureId": "9f2a...",
  "characterName": "Wren",
  "characterType": "Detective"
}
```

**Response (400 Bad Request)** — one or more fields missing or invalid; every failing field is
named (FR-005), so the frontend can point the player back at exactly what's missing:
```json
{
  "error": "invalid_setup",
  "message": "Setup is incomplete or invalid.",
  "fields": {
    "characterName": "Character name is required.",
    "characterType": "Select a character type for this adventure."
  }
}
```

Possible per-field messages:
- `adventureId`: `"Select an adventure."` (missing) — a nonexistent/unpublished id instead
  returns the 404 below, since that's a different failure than "field omitted."
- `characterName`: `"Character name is required."` (blank/whitespace-only) or
  `"Character name must be 50 characters or fewer."` (too long).
- `characterType`: `"Select a character type for this adventure."` (missing) or
  `"Choose one of this adventure's character types."` (not a member of the selected adventure's
  `characterTypes`).

**Response (404 Not Found)** — `adventureId` does not reference an existing, published story:
```json
{ "error": "not_found", "message": "Adventure not found" }
```

### Validation Rules (both new/changed endpoints)

- Every request MUST pass `authorize_player` (Constitution Principle II) — no anonymous access,
  and an authenticated non-Player (e.g., an Administrator with no Player role) gets
  `forbidden_insufficient_permission()`, same shape as the admin API's equivalent case.
- `GET /api/game/adventures` and `GET /api/game/adventures/{adventureId}` never include an
  unpublished story in any response, under any circumstance (FR-001, FR-006).
- `POST /api/game/start` re-validates all three fields independently on every call — there is
  no server-side "step" state to trust from a prior request; a request with any field
  missing/invalid is rejected with every failing field identified (FR-005), never just the
  first one found.
- `characterName` validation: trim leading/trailing whitespace before checking blank and length;
  reject if the trimmed value is empty or exceeds 50 characters (FR-002, edge cases).
- `characterType` validation MUST be checked against the *selected* adventure's character types
  specifically — the same type name valid for one adventure is not implicitly valid for another
  (FR-003a, FR-004a).
