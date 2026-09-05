# API Contract: Core Gameplay

**Feature**: 008-core-gameplay | **Date**: 2026-09-05

All endpoints require Entra ID auth + `Player` role (`authorize_player`, existing
middleware from `006-adventure-and-character-setup`) — no change to that middleware.

## POST /api/game/sessions

Creates a new Play Session and returns its opening narrative. Supersedes
`POST /api/game/start`'s role as the "setup complete" endpoint — `006`'s plan explicitly
deferred session creation to this feature. `POST /api/game/start` is retired; the frontend
calls this endpoint directly once setup (adventure, name, character type) is complete.

**Request**:

```json
{ "adventureId": "string", "characterName": "string", "characterType": "string" }
```

Validation is identical to `006`'s `POST /api/game/start` (adventure exists and is
published, `characterName` non-blank ≤50 chars, `characterType` is one of the adventure's
`characterTypes`) — same `FIELD_MESSAGES`/400 shape as `start.py` today (data-model.md
Validation Rules).

Creating a session also makes it the player's active session (FR-015): any other
`"active"`-status session belonging to this player is set `isActiveForPlayer = false` as
part of the same operation (data-model.md State Transitions) — no separate response field
for this; it's an internal side effect.

**Response (201 Created)**:

```json
{
  "status": "success",
  "sessionId": "uuid",
  "narrative": {
    "turnNumber": 0,
    "narrativeText": "string",
    "suggestedActions": ["string", "string", "string"],
    "locationLabel": "string",
    "goalLabel": "string|null",
    "progress": { "current": 1, "total": 5 }
  }
}
```

**Response (400 Bad Request)** — same `invalid_setup` shape as existing `start.py`.

**Response (404 Not Found)** — adventure doesn't exist or isn't published.

**Response (423 Locked)** — the player is within an active content-safety lockout
(FR-013, data-model.md Player Content-Safety Standing):

```json
{ "error": "content_safety_lockout", "message": "You're temporarily locked out due to repeated flagged submissions. Try again after {lockoutUntil}." }
```

Checked before any other validation or LLM call.

**Response (500)** — `LLMOutputError`/`LLMRateLimitError` from the opening-narrative call
maps to `error_response(502, "narrative_unavailable", "...")`; no session is persisted if
the opening narrative can't be generated (mirrors `004`'s "no partial write on LLM
failure" rule).

## POST /api/game/sessions/{sessionId}/interactions

Submits one natural-language player action and returns the resulting narrative turn, or
the session's already-concluded/rate-limited/concurrent-interaction state.

**Request**:

```json
{ "input": "string" }
```

- `input` non-blank after trim is the only client-side-checkable precondition; anything
  else (gibberish, off-fiction requests) is handled narratively by the LLM per Edge Cases,
  not rejected as invalid.
- A blank/whitespace-only `input` is rejected with 400
  `{"error": "invalid_input", "message": "Type an action to continue."}`.

**Response (200 OK)** — session remains active:

```json
{
  "status": "active",
  "narrative": {
    "turnNumber": 4,
    "narrativeText": "string",
    "suggestedActions": ["string", "string", "string"],
    "locationLabel": "string",
    "goalLabel": "string|null",
    "progress": { "current": 2, "total": 5 }
  }
}
```

**Response (200 OK)** — this interaction concludes the session:

```json
{
  "status": "concluded",
  "narrative": { "...": "same shape as above — the concluding narrative turn" },
  "completionReason": { "type": "success", "detail": "the player escaped the cove" }
}
```

`completionReason.type` is one of `"duration" | "success" | "failure"`;
`completionReason.detail` is the matched condition text, or `null` for `"duration"`.

**Response (409 Conflict)** — session already concluded (FR-010):

```json
{ "error": "session_concluded", "message": "This story has already ended." }
```

**Response (409 Conflict)** — a second interaction is already in flight for this session
(FR-006, Edge Cases):

```json
{ "error": "interaction_in_progress", "message": "Your last action is still being processed." }
```

**Response (409 Conflict)** — this session is not the player's current active session
(FR-015): the player interacted with a different one of their own sessions more recently
and hasn't resumed this one:

```json
{ "error": "session_inactive", "message": "You left this story to play another. Resume it to continue here." }
```

Checked after the 423 lockout check and before the concluded/in-progress/rate-limit
checks, and before any LLM call.

**Response (429 Too Many Requests)** — submitted faster than the allowed rate (FR-005):

```json
{ "error": "rate_limited", "message": "Slow down a little — take a breath before your next move." }
```

**Response (423 Locked)** — the player is within an active content-safety lockout
(FR-013): same shape as `POST /api/game/sessions` above. Checked before the
concluded/in-progress/rate-limit checks below and before any LLM call.

**Response (403 Forbidden)** — `sessionId` exists but `playerId != authenticated user`
(FR-006 exclusivity): same `forbidden_access_not_granted()` shape used elsewhere, never
revealing that the session exists to a non-owner.

**Response (404 Not Found)** — `sessionId` doesn't exist.

**Response (200 OK)** — unsafe content was screened out on either side (FR-004, Edge
Cases), or the input attempted to override the system's behavior/reveal its instructions
(FR-012): both are treated as a normal narrative turn whose `narrativeText` is a safe
in-fiction deflection (e.g., "That doesn't seem to work here.") — never a distinct error
shape, so the frontend needs no special-case handling and no flagged content or internal
prompt ever reaches the response body. A content-safety-flagged submission (but not an
FR-012 override attempt) additionally increments the player's flagged-submission count
server-side (FR-013) — invisible to this response's shape unless it is the 3rd such flag,
in which case `narrativeText` also explains the resulting 1-hour lockout.

## POST /api/game/sessions/{sessionId}/resume

Makes an existing, non-concluded session of the caller's own the player's active session
again (FR-015), deactivating whatever session is currently active for that player. Takes
no request body.

**Response (200 OK)**:

```json
{ "status": "active", "sessionId": "uuid" }
```

The frontend re-fetches/re-renders the resumed session's last turn from state it already
holds client-side — no narrative is generated by a resume (no LLM call), consistent with
there being no `GET /api/game/sessions/{sessionId}` endpoint (see Notes below).

**Response (403 Forbidden)** — `sessionId` exists but `playerId != authenticated user`,
same `forbidden_access_not_granted()` shape used elsewhere.

**Response (404 Not Found)** — `sessionId` doesn't exist.

**Response (409 Conflict)** — `status == "concluded"` (nothing to resume into) or
`isActiveForPlayer` is already `true` (already the active session):

```json
{ "error": "session_concluded", "message": "This story has already ended." }
```

```json
{ "error": "already_active", "message": "This is already your active story." }
```

## Notes

- Session summarization (FR-014) is entirely internal to how narrative context is
  assembled server-side — it never changes either endpoint's request/response shape.

- No `GET /api/game/sessions/{sessionId}` endpoint is introduced here — reconstructing an
  in-progress session after a page reload/navigation-away is `009-save-and-continue`'s
  concern (spec.md Assumptions); within one continuous browser session the frontend holds
  the current turn's state itself, and only needs the response shape above to render the
  next one.
- Error response envelopes (`{"error": ..., "message": ...}`) and status-code conventions
  match `src/backend/api/utils.py` exactly — no new helper needed beyond
  `error_response`/`json_response` already in use.
