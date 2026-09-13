# API Contract: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Feature**: `031-sessions-admin-design-spec`

One new endpoint, and a correction to the error codes four existing player endpoints return.

---

## NEW — `DELETE /api/manage/sessions/{sessionId}`

Permanently deletes one session — player or administrator test-play alike (spec FR-006).

**Authorization**: `authorize_admin` (Administrator role, enforced server-side, spec FR-010).
No body, no query parameters: the id alone determines which container holds the session
(research.md Decision 1).

| Outcome | Status | Body |
| --- | --- | --- |
| Deleted | 200 | `{"status": "deleted", "sessionId": "<id>"}` |
| No session with that id, in either container | 404 | `{"status": "error", "error": "not_found", "message": "Session not found"}` |
| Caller is signed in but not an administrator | 403 | existing `forbidden_insufficient_permission()` |
| Caller is not signed in / token invalid | 401 | existing `unauthorized(...)` |

The 404 is the concurrent-delete case (spec FR-015): a second administrator deleting the same
row gets it, and their table removes the row on the strength of it — the server has confirmed
the session is gone.

**Side effects**: the session document and everything on it (transcript, checkpoints, token
total). Nothing else. No `Story` is read or written, so `Story.totalTokens` and
`Story.lastTestPlayedAt` are untouched (spec FR-009, data-model.md).

---

## UNCHANGED — `GET /api/manage/sessions`

No change to request, response shape, ordering, or authorization. The screen is restyled
around exactly the rows it already returns.

---

## CORRECTED — `session_removed` replaces `story_deleted` for a missing session

Today a missing session and a missing story both answer `404 story_deleted`, which would tell a
player their story was deleted when only their session was (spec FR-012a, research.md
Decision 3). These four handlers in `backend/api/game/sessions.py` change:

| Endpoint | Today | After |
| --- | --- | --- |
| `POST /api/game/sessions/{id}/interactions` | `SessionNotFoundError` and `AdventureNotFoundError` → `404 story_deleted` | `SessionNotFoundError` → `404 session_removed`; `AdventureNotFoundError` → `404 story_deleted` *(unchanged)* |
| `POST /api/game/sessions/{id}/resume` | same conflation | same split |
| `GET /api/game/sessions/{id}` | same conflation | same split |
| `POST /api/game/sessions/{id}/checkpoints` | `SessionNotFoundError` → `404 not_found` | `SessionNotFoundError` → `404 session_removed` |

**The `session_removed` body**:

```json
{
  "status": "error",
  "error": "session_removed",
  "message": "This session has been removed. You can start this story again from your home page."
}
```

The message names no actor (research.md Decision 4) and offers a next action, per the
constitution's player-facing copy rules.

**Explicitly not changed**: `DELETE /api/game/sessions/{sessionId}` keeps `404 not_found`. A
player deleting a saved game that is already gone is not a bump, and nothing routes them
anywhere on it.

**Regression risk this carries**: any existing test asserting `story_deleted` for a *session*
that does not exist is asserting the behaviour being corrected and must be re-pointed at
`session_removed`; tests asserting `story_deleted` for a deleted *story* must keep passing
untouched. Telling the two apart is a required step of the implementation, not a cleanup.

---

## Frontend service surface

| Module | Change |
| --- | --- |
| `services/sessionService.js` | + `deleteSession(token, sessionId)` → `DELETE /manage/sessions/{id}`, same `X-Custom-Authorization` header as `listSessions` |
| `services/gameService.js` | no change — callers switch on `err.response.data.error`, which now carries the new code |
</content>
