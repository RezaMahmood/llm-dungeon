# API Contract Changes: Player Home Page Redesign

Only additions/changes are documented; every other existing `game/*` and `manage/*`
endpoint is unchanged.

## `DELETE /api/game/sessions/{sessionId}` (NEW)

Deletes the caller's own saved session permanently. Guarded by `authorize_player` (same
middleware as every other `game/sessions/*` route).

**Path params**: `sessionId` — the session to delete.

**Responses**:

| Status | Body | When |
|---|---|---|
| 200 | `{"status": "deleted", "sessionId": "..."}` | Session existed, belonged to the caller, and was deleted. |
| 404 | `{"error": "not_found", "message": "Session not found"}` | No session with that id exists. |
| 403 | Standard forbidden body (`forbidden_access_not_granted()`) | Session exists but belongs to a different player. |
| 401 | Standard unauthorized body | Caller not authenticated / not a player. |

The 200-with-body success shape matches this repo's established delete convention
(`delete_test_play_session` in `src/backend/api/admin/test_play.py` returns exactly this);
no endpoint in `src/backend/api/` currently returns 204.

Idempotent from the caller's perspective: a second delete of the same id (e.g. a
double-click) returns 404, not a 500 — matching `list_player_sessions`'s existing
"vanished mid-request" tolerance pattern (`delete_active_sessions_for_adventure`). **The
client treats that 404 as success** (the session is gone, which is what was asked) rather
than surfacing an error — spec.md Edge Cases.

## `GET /api/game/adventures` (CHANGED — additive field)

`AdventureSummary` gains one new field:

```diff
 {
   "id": "...",
   "name": "...",
   "tone": "...",
   "sessionLengthMinutes": 20,
-  "readingLevel": "Year 5"
+  "readingLevel": "Year 5",
+  "blurb": "Every door tells you a rule. Eight of them are lying."
 }
```

`blurb` is `Optional[str]`; a story published before this field existed returns `null`. The
frontend renders a `null` blurb as an empty blurb line rather than erroring (no story in
practice should ship without one once the wizard requires/encourages it, but this keeps
older data non-breaking).

## `PATCH /api/manage/stories/drafts/{draftId}` (CHANGED — additive field)

`blurb` joins the existing patchable field set (`name`, `coverImageUrl`, `tone`,
`readingLevel`, `sessionLengthMinutes`, `chapters`, `worldPrompt`, `rules`). Same
validation shape as `name`/`tone` (a plain string, no Shared-Structure validation).

## `GET /api/manage/stories/{storyId}/configuration` and story import (CHANGED — additive field)

The exported/imported configuration file gains `blurb` alongside `name`/`tone`/etc. Importing
a file without `blurb` (e.g. one exported before this feature) leaves it `null` — never a
validation failure.

## `GET /api/game/sessions` (UNCHANGED)

No shape change — `Session` summary fields listed in data-model.md are exactly what Home's
`InProgressList` consumes today.
