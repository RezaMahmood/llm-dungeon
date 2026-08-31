# API Contracts: Story Creation

**Date**: 2026-08-29 | **Revised**: 2026-08-31 (Session 2026-08-30 Clarifications: explicit Save/Abandon/Finished replaces the draft/generation endpoints below)

**Feature**: Story Creation (004-story-creation)

All endpoints require an authenticated Administrator (`authorize_admin`, per `src/backend/api/admin/middleware.py`), returning the same `unauthorized()`/`forbidden_access_not_granted()`/`forbidden_insufficient_permission()` shapes as existing admin endpoints on failure. Response shapes follow `src/backend/api/utils.py`'s `json_response`/`error_response` helpers.

The `POST/GET/PATCH /api/manage/stories/drafts*` endpoints from the original (auto-generate-on-completeness) design are removed entirely — there is no more server-side draft resource (research.md §7). They are replaced by the endpoints below, which act directly on `Story` records.

---

## POST /api/manage/stories

**Purpose**: Save (first write) — creates a new `Story` record (FR-004). This is the *only* way a Story is ever written to Cosmos; there is no automatic/implicit persistence.

**Request** (any subset of `Story`'s optional fields per data-model.md; `name` is the only required field):
```json
{
  "name": "The Lighthouse at Gullwing Cove",
  "outline": "A half-abandoned lighthouse on a cold northern cove in 1908...",
  "rules": "Nobody actually gets hurt.",
  "characterTypes": [
    { "name": "Curious Cousin", "description": "Visiting for the summer, unafraid to ask questions." }
  ],
  "completionCriteria": {
    "maxDurationMinutes": 20,
    "successConditions": ["The player learns what really happened to the keeper."],
    "failureConditions": [],
    "rule": null
  }
}
```

**Response (201 Created)**:
```json
{
  "status": "success",
  "story": {
    "id": "9f2a...",
    "name": "The Lighthouse at Gullwing Cove",
    "coverImageUrl": null, "tone": null, "readingLevel": null,
    "sessionLengthMinutes": null, "chapters": null,
    "outline": "A half-abandoned lighthouse on a cold northern cove in 1908...",
    "rules": "Nobody actually gets hurt.",
    "characterTypes": [ { "name": "Curious Cousin", "description": "..." } ],
    "completionCriteria": { "maxDurationMinutes": 20, "successConditions": ["..."], "failureConditions": [], "rule": null },
    "published": false,
    "createdBy": "admin@example.com", "createdAt": "2026-08-31T20:00:00Z",
    "updatedBy": "admin@example.com", "updatedAt": "2026-08-31T20:00:00Z"
  }
}
```

**Response (422 Unprocessable Entity)** — `name` missing/empty, or a supplied `characterTypes`/`completionCriteria` entry fails Shared Structure validation:
```json
{ "error": "invalid_field", "message": "name is required" }
```

---

## PATCH /api/manage/stories/{storyId}

**Purpose**: Save (later write) — updates an existing `Story` record in place (FR-004). Any subset of fields; unspecified fields are left unchanged.

**Request**: same shape as `POST`'s body, any subset (including `name`, but it cannot be cleared to empty).

**Response (200 OK)**: updated `story`, same shape as `POST`'s response, with `updatedBy`/`updatedAt` refreshed to the current administrator/time.

**Response (404 Not Found)** — the story doesn't exist (e.g. it was Abandoned from another tab/session):
```json
{ "error": "not_found", "message": "Story not found" }
```

**Response (422 Unprocessable Entity)** — same validation rules as `POST`.

---

## DELETE /api/manage/stories/{storyId}

**Purpose**: Abandon (FR-013/014) — deletes the `Story` record. Idempotent: deleting a story that was never saved (or already deleted) is a no-op success, not an error (Edge Cases).

**Response (200 OK)**:
```json
{ "status": "success" }
```

---

## POST /api/manage/stories/{storyId}/cover-image

**Purpose**: Uploads a Tab 01 cover image to blob storage and stores the reference on the Story (FR-009). The story must already exist — the wizard always Saves the story's fields first (creating it if necessary) before uploading a pending cover image, so this call always targets a real `storyId`.

**Request**: raw file bytes as the request body, with `Content-Type` set to the file's MIME type and `X-File-Name` set to its filename.

**Response (200 OK)**: updated `story` (same shape as `POST /api/manage/stories`'s response) with `coverImageUrl` set to the blob's URL.

**Response (404 Not Found)** — no story exists yet for `storyId`.

---

## POST /api/manage/stories/suggest-outline

**Purpose**: Tab 02's one-shot "Suggest" action (FR-003) — no story needs to exist yet; this call is independent of Save.

**Request**:
```json
{ "idea": "A half-abandoned lighthouse on a cold northern cove in 1908..." }
```

**Response (200 OK)**:
```json
{ "status": "success", "outline": "A half-abandoned lighthouse..." }
```

**Response (422 Unprocessable Entity)** — `idea` missing/empty:
```json
{ "error": "invalid_field", "message": "idea is required" }
```

**Response (502 Bad Gateway)** — the LLM call failed or returned output that failed validation (Edge Cases: the administrator's existing outline text box is left untouched on this response — the frontend never applies a failed suggestion):
```json
{ "error": "generation_failed", "message": "Could not generate a suggested outline right now; please try again" }
```

---

## GET /api/manage/stories

**Purpose**: List all persisted stories.

**Response (200 OK)**:
```json
{
  "status": "success",
  "stories": [
    { "id": "9f2a...", "name": "The Lighthouse at Gullwing Cove", "published": false, "createdAt": "2026-08-31T20:00:00Z" }
  ]
}
```
List entries are summaries (`id`, `name`, `published`, `createdAt`); full detail is fetched via the endpoint below.

---

## GET /api/manage/stories/{storyId}

**Purpose**: Fetch one persisted story's full configuration (used by the wizard to reload a saved story, and by `005-story-publishing`/`012-story-editing-and-review` later).

**Response (200 OK)**: same `story` shape as `POST /api/manage/stories`'s response.

**Response (404 Not Found)**:
```json
{ "error": "not_found", "message": "Story not found" }
```

### Validation Rules (all endpoints)

- Every request MUST pass `authorize_admin` (Constitution Principle II) — no anonymous access to any story data.
- `characterTypes`/`completionCriteria` writes are validated against the Shared Structures in data-model.md before merge; the first invalid field short-circuits the write with a `422` (no partial merge of a rejected field alongside accepted ones in the same request).
- `createdBy`/`updatedBy` are always taken from the authenticated admin session's email claim (FR-012), never from the request body.
- Persistence happens only on `POST`/`PATCH`/the cover-image upload — no endpoint has a side effect of writing a `Story` as a byproduct of another action (e.g. `suggest-outline` never touches Cosmos).
