# Phase 1 Data Model: Player Home Page Redesign

One new field (`Story.blurb`, mirrored on `StoryDraft`) is introduced. Everything else
composes two existing entities' existing player-facing summary shapes and adds one deletion
operation.

## Story (existing — `StoryService.list_published_summaries`)

`list_published_summaries` today projects, per published story: `id`, `name`, `tone`,
`sessionLengthMinutes`, `readingLevel`. Home's "Ready to play" row maps these to the
canonical kicker (`{tone} · {sessionLengthMinutes} min` — `tone` is what the design calls
the story's genre), title (`name`), and `Reading level: {readingLevel}`.

### New field: `blurb`

The canonical row requires a short player-facing blurb (spec.md FR-016). `Story`
(`src/backend/models/story.py`) has **no** field carrying that today — its text fields are
`worldPrompt` and `narrativeGuidance` (LLM-authoring inputs, not player copy); the only
`description` in that module belongs to `CharacterType`. So `blurb: Optional[str] = None`
is added to both `Story` and `StoryDraft`, authored as a plain administrator-set field
(research.md Decision 5) and added to the projection above.

`Optional` rather than required: stories published before this field existed have no blurb,
and must keep loading (contracts/api.md).

## Session (existing — `PlaySessionService.list_player_sessions` / `_session_summary_from_row`)

Unchanged shape, already returns per in-progress session: `sessionId`, `adventureId`,
`adventureName`, `characterName`, `locationLabel`, `progress`, `turnCount`, `startedAt`,
`lastInteractionAt`, `isActiveForPlayer`, `checkpointCount`, `available`.

Home's `SessionCard` maps: `adventureName` → title; `progress` → both the chapter
(`Chapter {progress.current}`) and the segmented bar (`progress.current` filled of
`progress.total`), exactly as `SavedGameRow.jsx` renders them today; `lastInteractionAt` →
the "last played" phrase (`SavedGameRow.jsx`'s `formatLastPlayed`, reused);
`locationLabel` → location; `available` → the unavailable state required by FR-018 (a story
unpublished or deleted under a live session — `SavedGameRow.jsx` today dims the row, tags it
"Unavailable" and disables Resume; the card must carry equivalent treatment, restyled to the
canonical card). No new field is added to this summary.

### New operation: delete a player's own session

```
PlaySessionService.delete_player_session(session_id: str, player_id: str) -> None
```

- Reads the session; raises `SessionNotFoundError` if absent (idempotent 404, matching
  `get_session`'s existing error shape).
- Raises `ForbiddenError` if `session.playerId != player_id` (matching every other
  player-ownership check in this service — never trusts a client-supplied owner).
- On success, hard-deletes the Cosmos item (same primitive as
  `delete_active_sessions_for_adventure`).
- No return value; the endpoint responds `200` with `{"status": "deleted", "sessionId": …}`,
  matching the repo's existing delete convention (contracts/api.md).

## State transition

```
Session exists, playerId = P
        │  DELETE /game/sessions/{id} as P
        ▼
Session document removed permanently
        │
        ▼
list_player_sessions(P) no longer includes it  →  the story reappears in
list_published_summaries() minus "already has an active session" filtering
(Home's own composition step — see contracts/api.md), i.e. in "Ready to play"
```
