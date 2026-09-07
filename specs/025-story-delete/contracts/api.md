# API Contracts: Story Delete

**Date**: 2026-09-07

**Feature**: Story Delete (025-story-delete)

Adds one endpoint to `src/backend/api/admin/stories.py`, and changes error-response mappings and one list response shape in `src/backend/api/game/sessions.py` (`008-core-gameplay-done`, `009-save-and-continue`). Response shapes follow `src/backend/api/utils.py`'s `json_response`/`error_response` helpers, matching existing conventions.

---

## DELETE /api/manage/stories/{storyId}

**Purpose**: Permanently delete a story's configuration (FR-003), and permanently delete every in-progress (`status == 'active'`) `PlaySession` referencing it (FR-004). Requires an authenticated Administrator (`authorize_admin`), returning the same `unauthorized()`/`forbidden_access_not_granted()`/`forbidden_insufficient_permission()` shapes as existing admin endpoints on failure.

Reachable only from the administrator story list's per-row delete action (FR-001), behind the client-side confirmation prompt of FR-002 — there is no server-side precondition beyond the story existing (FR-003).

**Request**: No body.

**Response (200 OK)** — story and its in-progress sessions permanently removed:
```json
{
  "status": "deleted",
  "storyId": "9f2a..."
}
```

No `story` object is returned — there is nothing left to describe. The administrator story list removes the row in place from this response alone (FR-012).

**Response (404 Not Found)** — no story exists with this id (never existed, or already deleted; FR-013):
```json
{ "error": "not_found", "message": "Story not found" }
```

### Validation Rules

- Every request MUST pass `authorize_admin` (Constitution Principle II) — no anonymous access.
- The endpoint accepts no request body.
- Deleting an already-deleted story id returns the same 404 shape as deleting one that never existed — unlike publish/unpublish, a repeat delete is not treated as an idempotent success.

---

## Changed: POST /api/game/sessions/{sessionId}/interactions

**Purpose (unchanged)**: Submit a player turn (`008-core-gameplay-done`). This feature changes the response for two cases: the session's story was deleted, or the session's story was merely unpublished. These are reported differently (FR-007, FR-008).

**Response (404 Not Found)** — the session no longer exists, because a story delete permanently removed it, or (a narrow race) a turn was already in flight at the exact moment of deletion:
```json
{
  "error": "story_deleted",
  "message": "Story has been deleted. You can no longer continue this story.",
  "promptReturnToList": true
}
```

**Response (409 Conflict)** — the session still exists, but its story has since been unpublished:
```json
{
  "error": "story_unpublished",
  "message": "Story has been unpublished. You can no longer continue this story.",
  "promptReturnToList": true
}
```

This replaces the previous, undifferentiated `{"error": "not_found", "message": "Session not found"}` / `{"error": "not_found", "message": "Adventure not found"}` bodies for this endpoint. `POST /api/game/sessions` (starting a *new* game) and `GET /api/game/adventures/{adventureId}` are unrelated flows and keep their existing `not_found` responses unchanged.

## Changed: POST /api/game/sessions/{sessionId}/resume

Applies the same two checks as above, for the same reason: a player resuming a session belonging to a deleted story gets `404 story_deleted`; one belonging to an unpublished story gets `409 story_unpublished` instead of the resume flow's prior success/`already_active`/`session_concluded` outcomes.

## Changed: GET session detail (rehydrating the play surface, `get_session_detail_for_player`)

Applies the same two checks: reading full detail for a session whose story is now deleted or unpublished returns the same `404 story_deleted` / `409 story_unpublished` shapes above, so a player who navigates directly back into an affected session (rather than submitting a turn first) sees the specific reason immediately.

### Validation Rules (all three changed endpoints)

- No change to authorization, rate-limiting, content-safety, or any other existing behavior on these endpoints — only the story-deleted/story-unpublished checks and their response shapes are added.
- The frontend MUST render `story_deleted` and `story_unpublished` as two distinct, specific notices (FR-007, FR-008) — not a shared generic message — each including a "return to your list of in-progress games" call to action (`promptReturnToList`).

---

## Changed: GET (player's list of in-progress games — `list_player_sessions`, per `009-save-and-continue`'s contract)

Each row gains one new field:

```json
{
  "id": "...",
  "adventureId": "...",
  "adventureName": "...",
  "available": true,
  "...": "... (existing fields unchanged)"
}
```

- `available: false` — this session's story has been unpublished; the frontend renders the row greyed out / non-continuable (FR-009).
- `available: true` — normal, continuable row (the default/existing behavior for a published story's session).
- A session belonging to a *deleted* story never appears in this response at all (FR-010) — its row no longer exists to return, so no `available` value is needed for that case.

`available` is computed fresh on every call against the story's *current* `published` value — a story that is re-published after being unpublished causes `available` to revert to `true` on the very next call, with no separate action (FR-011).
