# Phase 1 Data Model: Player Home Page Redesign

No new persisted entity or field is introduced. This feature composes two existing
entities' existing player-facing summary shapes and adds one deletion operation.

## Story (existing — `StoryService.list_published_summaries`)

Unchanged. Already returns, per published story: `id`, `name`, `tone`, `sessionLengthMinutes`,
`readingLevel`. Home's "Ready to play" row maps these to the design's kicker
(`{tone} · {sessionLengthMinutes} min`), title (`name`), and `Reading level: {readingLevel}`.

The design spec's `blurb` field (`type Story { blurb: string }`, spec.md §10) has **no
existing backend source** — `list_published_summaries`'s Cosmos projection does not select
it. Resolution (recorded here, not deferred, since it blocks FR-002): the story's existing
`Story` document already carries a description-shaped field from story creation
(`004-story-creation`); the plan's tasks add that field to the `list_published_summaries`
projection rather than inventing new story metadata, keeping this feature's Assumption ("no
new story metadata") intact. Tasks.md verifies the exact existing field name against
`src/backend/models/story.py` before wiring it through — this is an implementation detail,
not a schema change.

## Session (existing — `PlaySessionService.list_player_sessions` / `_session_summary_from_row`)

Unchanged shape, already returns per in-progress session: `sessionId`, `adventureId`,
`adventureName`, `characterName`, `locationLabel`, `progress`, `turnCount`, `startedAt`,
`lastInteractionAt`, `isActiveForPlayer`, `checkpointCount`, `available`.

Home's `SessionCard` maps: `adventureName` → title, `progress`/`turnCount` → the chapter and
segmented bar (existing `SavedGameRow.jsx` already derives a chapter number and a
completed/total pair from this shape — reused as-is), `lastInteractionAt` → the preformatted
"last played" phrase (existing `SavedGameRow.jsx` formatting logic, reused), `locationLabel`
→ location. No new field is added to this summary for display purposes.

### New operation: delete a player's own session

```
PlaySessionService.delete_player_session(session_id: str, player_id: str) -> None
```

- Reads the session; raises `SessionNotFoundError` if absent (idempotent 404, matching
  `get_session`'s existing error shape).
- Raises `ForbiddenError` if `session.playerId != player_id` (matching every other
  player-ownership check in this service — never trusts a client-supplied owner).
- On success, hard-deletes the Cosmos item (same primitive as
  `delete_active_sessions_for_adventure`), regardless of `status` (`active` or `concluded`)
  — a player may also want to clear a finished session from history; nothing in the spec
  restricts deletion to in-progress sessions, and disallowing it would need a new state the
  spec doesn't call for.
- No return value; the caller (the DELETE endpoint) responds `204 No Content` on success.

## State transition

```
Session exists, status = "active" or "concluded", playerId = P
        │  DELETE /game/sessions/{id} as P
        ▼
Session document removed permanently
        │
        ▼
list_player_sessions(P) no longer includes it  →  the story reappears in
list_published_summaries() minus "already has an active session" filtering
(Home's own composition step — see contracts/api.md), i.e. in "Ready to play"
```
