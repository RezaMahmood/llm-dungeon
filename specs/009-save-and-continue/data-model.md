# Data Model: Save and Continue

**Feature**: 009-save-and-continue | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

This feature adds **no new Cosmos container** and no new top-level document type. It adds
one embedded structure to the `PlaySession` document `008-core-gameplay` already writes
(`src/backend/models/play_session.py`, container `playSessions`, partition key `/id`), and
two read shapes derived from documents that already exist.

Spec Key Entity mapping: **Saved Game** is `PlaySession` with `status == "active"` — not a
new entity, which is why nothing below re-declares it. **Checkpoint Marker** is the new
embedded structure.

---

## New Structure: Checkpoint Marker (embedded in `PlaySession.checkpoints`)

Not a top-level Cosmos document — stored only inside its parent session, mirroring how
`PlayerInteraction` is stored inside `turns` (research.md Decision 1).

| Field | Type | Notes |
|-------|------|-------|
| `label` | string | The `locationLabel` of the session's latest turn at the moment of the save; `"Your story"` when that turn carries no location. System-generated — the player is never asked to name a checkpoint (FR-003, research.md Decision 2) |
| `turnNumber` | integer | `turnNumber` of the latest turn at the moment of the save; `0` for a save taken before any player action |
| `createdAt` | ISO 8601 timestamp (UTC) | When the save was recorded. The player-facing "labelled, timestamped" string is composed client-side from `label` + `createdAt` |

### Validation & Invariants

- `checkpoints` is **append-only** — no existing marker is ever edited, reordered, or
  removed, and markers are stored oldest-first (FR-003a).
- A marker holds **no copy of game state**. It cannot be resumed from, and recording one
  never changes `turns`, `status`, `summary`, or any other session field (FR-003a).
- Recording a marker never advances or alters `lastInteractionAt` — a save is not a turn,
  and must not shift the rate-limit window `008` derives from that field.
- Two markers may share the same `turnNumber` (the player saved twice without acting in
  between); this is the expected no-op-save outcome, and both are kept (spec Edge Case 3).
- A marker is only ever recorded on a session with `status == "active"`; a concluded game
  has nothing further to save (FR-004, spec Edge Case 2).
- Every write is a read-modify-write with an `if-match` ETag precondition and at most one
  retry, so a checkpoint can never overwrite a turn that landed concurrently
  (research.md Decision 8).

### Change to `PlaySession`

| Field | Type | Notes |
|-------|------|-------|
| `checkpoints` | array of Checkpoint Marker | **NEW.** Defaults to `[]`. Absent on every session written before this feature; `from_dict` must treat a missing field as `[]` so existing documents keep loading unchanged |

No other `PlaySession` field changes. No migration or backfill is required — a session with
no `checkpoints` key is simply a game that has never been explicitly saved.

---

## Derived Read Shape: Saved Game Summary (`GET /api/game/sessions`)

Projected per row from a `PlaySession` plus its adventure's `Story`; not persisted anywhere.

| Field | Source | Notes |
|-------|--------|-------|
| `sessionId` | `PlaySession.id` | |
| `adventureId` | `PlaySession.adventureId` | |
| `adventureName` | `Story.name` via `StoryService.get_story` | `"Adventure"` when the story can no longer be read (research.md Decision 4) |
| `characterName` | `PlaySession.characterName` | Distinguishes two games on the same adventure (spec Edge Case 4) |
| `locationLabel` | `turns[-1].locationLabel` | The design's "…· The keeper's stairs" |
| `progress` | `turns[-1].progress` | `{current, total}` or `null`; drives the design's progress bars |
| `turnCount` | `len(turns)` | |
| `startedAt` | `PlaySession.startedAt` | |
| `lastInteractionAt` | `PlaySession.lastInteractionAt` | The design's "Last played yesterday"; also the sort key |
| `isActiveForPlayer` | `PlaySession.isActiveForPlayer` | Marks the current game in the list, and decides whether resuming needs `POST .../resume` (FR-001, research.md Decision 5) |
| `checkpointCount` | `len(checkpoints)` | Lets the list show that a game has been explicitly saved without shipping every marker |

Rows carry **no `turns` array** — the full history belongs to the detail read below.

### Selection & Ordering

- Only sessions whose `playerId` equals the authenticated user. Enforced in the query
  itself, server-side; never filtered client-side (Principle II, FR-001, SC-002).
- Only `status == "active"` — concluded games are not "in progress" and must not appear
  (FR-001, spec Edge Case 2).
- Ordered by `lastInteractionAt` descending (most recently played first), matching
  `02-story-select.html`'s ordering.
- An empty result is a normal, successful response — the "nothing to continue" message is a
  rendering decision, not an error (FR-002).

---

## Derived Read Shape: Saved Game Detail (`GET /api/game/sessions/{sessionId}`)

The full session, sufficient to rebuild the play surface exactly as the player left it
(FR-006): every field of the Saved Game Summary above, plus `status`, `completionReason`,
`characterType`, the complete `turns` array (each turn exactly as `PlayerInteraction`
serialises it today), and `checkpoints`.

Ownership is checked before anything is returned: a session belonging to another player
gets the same generic 403 `submit_interaction` already returns, never a 404 that would
confirm the id exists (Principle II, FR-001).

---

## State Transitions

Checkpoint markers introduce no state machine of their own — `PlaySession.status` and
`isActiveForPlayer` continue to transition exactly as `008-core-gameplay/data-model.md`
defines. The two new operations sit alongside those transitions:

```
PlaySession (status="active")
  → POST .../checkpoints  (FR-003, FR-005)
      - reject (403) if playerId != authenticated user — before any state is revealed
      - reject (404) if the session does not exist
      - reject (409) if status == "concluded"
      - else: append {label, turnNumber, createdAt} to checkpoints and write with an
        if-match ETag precondition; on precondition failure, re-read and retry once
      - turns, status, summary, lastInteractionAt and isActiveForPlayer are all unchanged
      - a failure after the retry is reported to the client, which proceeds with the
        player's departure regardless (FR-006a, research.md Decision 7)

  → GET /api/game/sessions           — read-only projection, no state change
  → GET /api/game/sessions/{id}      — read-only, no state change
```

The continue flow's resume step is unchanged `008` behaviour: `POST .../resume` when the
chosen game is not the player's active one, skipped entirely when it already is
(FR-001a, research.md Decision 5).

---

## Cost & Scale

One extra small array on a document that already carries the full narrative history —
negligible against `turns`. The list endpoint is one cross-partition query on `playerId`
(the same query shape `_deactivate_other_active_sessions` already issues) plus one point
read per distinct adventure. No pagination or marker-count cap is built: the project has no
stated scale requirement, and a marker is three fields (Principle IV).
