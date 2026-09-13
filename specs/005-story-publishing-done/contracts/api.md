# API Contracts: Story Publishing

**Date**: 2026-08-30

**Feature**: Story Publishing (005-story-publishing)

Adds two endpoints to `src/backend/api/admin/stories.py` (as introduced by `004-story-creation-done`; the `manage/stories` in the URLs below is the route prefix registered in `function_app.py`, not the file path — see plan.md's Sequencing note). Both require an authenticated Administrator (`authorize_admin`), returning the same `unauthorized()`/`forbidden_access_not_granted()`/`forbidden_insufficient_permission()` shapes as existing admin endpoints on failure. Response shapes follow `src/backend/api/utils.py`'s `json_response`/`error_response` helpers, matching `004-story-creation-done/contracts/api.md`'s conventions.

Both endpoints are reachable from two callers with no difference in behavior (FR-010): the story-authoring wizard's "Publish & assign" step and the administrator story list's per-row action. Both are delivered by this feature — the list entry point in Phase 5, added by the 2026-09-06 scope revision — and `012-story-editing-and-review` reuses that same list action rather than adding a third caller.

---

## POST /api/manage/stories/{storyId}/publish

**Purpose**: Publish a story, making it visible in the player-facing adventure list (FR-003). Idempotent (FR-006). Blocked by the FR-008 test-play gate.

**Request**: No body.

**Response (200 OK)** — gate satisfied, story is now published (or was already published — same response either way, FR-006):
```json
{
  "status": "success",
  "story": {
    "id": "9f2a...",
    "published": true,
    "lastPublishedAt": "2026-08-30T14:22:00Z"
  }
}
```

**Response (404 Not Found)**:
```json
{ "error": "not_found", "message": "Story not found" }
```

**Response (409 Conflict)** — FR-008 gate not satisfied (no qualifying test-play exchange since content was last saved), FR-011's required explanatory text:
```json
{
  "error": "test_play_required",
  "message": "This story must be test-played since its last content change before it can be published."
}
```

**Response (409 Conflict)** — a concurrent write to the same story won the `_etag` race twice, so the publish-state change was not applied (issue #281). The write is conditional precisely so a racing content write cannot be silently clobbered; the client may retry:
```json
{
  "error": "write_conflict",
  "message": "Another change to this story landed at the same time. Try again."
}
```

---

## POST /api/manage/stories/{storyId}/unpublish

**Purpose**: Unpublish a previously published story, removing it from the player-facing adventure list (FR-004). Idempotent (FR-006). Never affects in-progress play sessions (FR-005). The "are you sure?" confirmation (FR-013) is enforced client-side only, before this call is made; the write itself carries an `_etag` precondition (issue #281), so a story deleted mid-write is never resurrected and a lost race surfaces as `409` rather than overwriting the winner.

**Request**: No body.

**Response (200 OK)** — story is now unpublished (or was already unpublished — same response either way, FR-006); `lastPublishedAt` is unchanged (FR-012):
```json
{
  "status": "success",
  "story": {
    "id": "9f2a...",
    "published": false,
    "lastPublishedAt": "2026-08-30T14:22:00Z"
  }
}
```

**Response (404 Not Found)**:
```json
{ "error": "not_found", "message": "Story not found" }
```

**Response (409 Conflict)** — a concurrent write to the same story won the `_etag` race twice, so the publish-state change was not applied (issue #281). The write is conditional precisely so a racing content write cannot be silently clobbered; the client may retry:
```json
{
  "error": "write_conflict",
  "message": "Another change to this story landed at the same time. Try again."
}
```

### Validation Rules (both endpoints)

- Every request MUST pass `authorize_admin` (Constitution Principle II) — no anonymous access.
- Neither endpoint accepts a request body; `published`, `lastPublishedAt`, `contentUpdatedAt`, and `lastTestPlayedAt` are never client-writable (data-model.md Validation Rules).
- `GET /api/manage/stories` (existing, `004`) and `GET /api/manage/stories/{storyId}` (existing, `004`) responses gain `lastPublishedAt` in their `story`/summary shapes; no other existing field or response shape changes.
