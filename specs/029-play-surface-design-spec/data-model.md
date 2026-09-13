# Phase 1 Data Model: Play Surface Design-Spec Conformance

No new field, entity, or schema change. This feature reads the existing turn shape
differently on the client; nothing changes on the wire or in Cosmos DB.

## Turn (existing — `PlayerInteraction`, `src/backend/models/play_session.py`)

Already returned, unchanged, by `POST /api/game/sessions/{sessionId}/interactions` and
`GET /api/game/sessions/{sessionId}` (`sessions.py`'s `_narrative_dict` /
`get_session_detail_for_player`):

```ts
type Turn = {
  turnNumber: number;
  narrativeText: string;
  suggestedActions: string[];   // up to three
  locationLabel: string;
  goalLabel?: string | null;
  progress?: { current: number; total: number } | null;
  playerInput?: string | null;  // absent/null on the opening turn
};
```

### New client-side derivations (no backend change)

- **Chapter identifier** (research.md Decision 1): `progress.current` → the pinned numeral;
  `locationLabel` of the same turn → the chapter's title. Present only when `progress` is
  non-null on the latest turn (spec.md FR-002's "when the active story reports
  chapter/progress information").
- **Spelling suggestion** (research.md Decision 2): computed client-side from the player's
  just-submitted text against `suggestedActions` on the *resulting* turn (the words the
  story now offers as next moves) using a simple near-miss comparison; held only in
  component state, never persisted or sent to the server.

## Session status (existing — unchanged)

`status: "active" | "concluded"` and `completionReason: { type, detail? } | null`, exactly as
consumed today by `PlayPage`. The play screen's Refresh action (research.md Decision 4)
re-reads these two fields plus the full `turns` array via the existing
`get_session_detail_for_player` shape — no new field is added to that response either.

## No state transitions introduced

This feature adds no new persisted state machine. The hint disclosure (research.md
Decision 3) and the spelling-suggestion note (Decision 2) are transient, client-only UI
state (open/closed, shown/cleared) that never reaches the server and has no bearing on
session status.
