# API Contract: Save and Continue

**Feature**: 009-save-and-continue | **Date**: 2026-09-06

Three new endpoints on the existing `game/sessions` route family. All require Entra ID auth
+ `Player` role via the existing `authorize_player` middleware — unchanged, no new
middleware. `008-core-gameplay-done`'s three endpoints (`POST /api/game/sessions`,
`POST .../interactions`, `POST .../resume`) are **unchanged by this feature**, including
`resume`'s `409 already_active` response (research.md Decision 5).

Every endpoint below checks `playerId == authenticated user` server-side before revealing
anything about a session (Principle II).

---

## GET /api/game/sessions

Lists the authenticated player's own in-progress games, newest activity first. Backs the
"stories in progress" section of `specs/designs/02-story-select.html` (FR-001, FR-002) and
the sign-out prompt's "is a game in progress?" check (FR-004, research.md Decision 6).

**Request**: no body, no parameters.

**Response (200 OK)**:

```json
{
  "status": "success",
  "sessions": [
    {
      "sessionId": "uuid",
      "adventureId": "uuid",
      "adventureName": "The Lighthouse at Gullwing Cove",
      "characterName": "Bramble",
      "locationLabel": "The keeper's stairs",
      "progress": { "current": 3, "total": 5 },
      "turnCount": 12,
      "startedAt": "2026-09-01T18:22:04Z",
      "lastInteractionAt": "2026-09-05T20:11:47Z",
      "isActiveForPlayer": true,
      "checkpointCount": 2
    }
  ]
}
```

- Only sessions with `status == "active"` and `playerId == authenticated user` are
  returned — another player's games are never listed, and a concluded game is never listed
  (FR-001, SC-002, spec Edge Case 2).
- Sorted by `lastInteractionAt` descending.
- `progress` is `null` when the latest turn carries none; `adventureName` falls back to
  `"Adventure"` when the story can no longer be read (research.md Decision 4).
- **No `turns`** — the narrative history comes from the detail read below.

**Response (200 OK, no games)**:

```json
{ "status": "success", "sessions": [] }
```

An empty list is a success, not a 404 — the client renders the "nothing to continue"
message from it (FR-002).

---

## GET /api/game/sessions/{sessionId}

Returns one of the player's own sessions in full, so the play surface can be rebuilt
exactly as they left it (FR-006).

**Request**: no body.

**Response (200 OK)**:

```json
{
  "status": "success",
  "session": {
    "sessionId": "uuid",
    "adventureId": "uuid",
    "adventureName": "The Lighthouse at Gullwing Cove",
    "characterName": "Bramble",
    "characterType": "Scout",
    "status": "active",
    "completionReason": null,
    "isActiveForPlayer": true,
    "locationLabel": "The keeper's stairs",
    "progress": { "current": 3, "total": 5 },
    "turnCount": 12,
    "checkpointCount": 1,
    "startedAt": "2026-09-01T18:22:04Z",
    "lastInteractionAt": "2026-09-05T20:11:47Z",
    "turns": [
      {
        "turnNumber": 0,
        "playerInput": null,
        "narrativeText": "string",
        "suggestedActions": ["string"],
        "locationLabel": "string",
        "goalLabel": "string|null",
        "progress": { "current": 1, "total": 5 },
        "timestamp": "2026-09-01T18:22:04Z"
      }
    ],
    "checkpoints": [
      { "label": "The keeper's stairs", "turnNumber": 11, "createdAt": "2026-09-05T20:12:03Z" }
    ]
  }
}
```

`turns` is the complete history, oldest first — identical in shape to what
`POST .../interactions` returns per turn, so the client renders resumed and live turns
through the same component.

**Response (403 Forbidden)** — the session belongs to another player. The same generic
`forbidden_access_not_granted()` body `submit_interaction` already returns; never a
different status or message that would confirm the id exists.

**Response (404 Not Found)**:

```json
{
  "error": "story_deleted",
  "message": "Story has been deleted. You can no longer continue this story.",
  "promptReturnToList": true
}
```

Concluded sessions **are** readable here (a player may open a finished game's record);
only the *list* excludes them.

**Note (post-`025-story-delete`)**: this handler's 404 reuses the same
`story_deleted`/`promptReturnToList` body it returns when the session's story was
deleted, because both a missing session and a deleted-story session resolve the same
way for this endpoint — there is nothing left to rebuild the play surface from either
way. `POST .../checkpoints` below was not touched by `025-story-delete` and still
returns the plain `{"error": "not_found", "message": "Session not found"}` body for an
unknown id, so the two endpoints now intentionally differ: only the detail read needs
to tell the client to prompt a return to the stories list.

---

## POST /api/game/sessions/{sessionId}/checkpoints

Records a checkpoint marker on the player's game — the explicit "Save a checkpoint"
action, the "Save and exit to my stories" action, and an accepted sign-out save prompt all
call this one endpoint (FR-003, FR-005).

**Request**: no body. The label is generated server-side from the session's own latest turn
— the client never supplies one, and a supplied one is ignored (FR-003, research.md
Decision 2).

**Response (201 Created)**:

```json
{
  "status": "success",
  "checkpoint": { "label": "The keeper's stairs", "turnNumber": 11, "createdAt": "2026-09-05T20:12:03Z" }
}
```

The response carries the marker so the client can show the brief visible confirmation the
constitution requires ("Checkpoint saved at The keeper's stairs") without a second read.

Recording a checkpoint changes nothing else about the session: no turn is added,
`lastInteractionAt` is untouched (a save is not a turn and must not shift the rate-limit
window), and `isActiveForPlayer`/`status` are unchanged (FR-003a).

**Response (403 Forbidden)** — session belongs to another player; same generic body as above.

**Response (404 Not Found)** — no such session.

**Response (409 Conflict)**:

```json
{ "error": "session_concluded", "message": "This story has already ended." }
```

A concluded game has nothing further to save (FR-004, spec Edge Case 2). Reuses the exact
error code `submit_interaction` already returns for the same condition.

**Response (503 Service Unavailable)**:

```json
{ "error": "checkpoint_unavailable", "message": "Couldn't record that checkpoint." }
```

Returned when the conditional write still fails after its one retry (research.md Decision
8). This is the case FR-006a governs: the client shows its "we couldn't record that
checkpoint, but your progress is safe" notice and **completes the sign-out or return home
anyway** — it must never block, delay, or reverse the player's departure.

---

## Notes for implementers

- Idempotency: repeated `POST .../checkpoints` calls each append a marker. Two markers at
  the same `turnNumber` is the correct, expected outcome of saving twice without acting in
  between (spec Edge Case 3) — do not de-duplicate.
- Rate limiting: checkpoints are deliberately **not** rate-limited. They cost no LLM call
  and one small conditional write, and throttling the "save before I leave" action is
  exactly the wrong failure mode.
- The client never calls `POST .../resume` for a game whose list row already reports
  `isActiveForPlayer: true`, and treats a `409 already_active` from a stale row as success
  (FR-001a, spec Edge Case 5, research.md Decision 5).
