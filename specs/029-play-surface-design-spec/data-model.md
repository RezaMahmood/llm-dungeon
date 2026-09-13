# Phase 1 Data Model: Play Surface Design-Spec Conformance

No new field, entity, or schema change. This feature reads the existing turn shape
differently on the client; nothing changes on the wire or in Cosmos DB.

## Turn (existing — `PlayerInteraction`, `src/backend/models/play_session.py`)

Already returned, unchanged, by `POST /api/game/sessions/{sessionId}/interactions` and
`GET /api/game/sessions/{sessionId}` (`sessions.py`'s `_narrative_dict`, and
`play_session_service.py`'s `get_session_detail_for_player`):

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

## Session status (existing — unchanged)

`status: "active" | "concluded"` and `completionReason: { type, detail? } | null`, exactly as
consumed today by `PlayPage`. The play screen's Refresh action (research.md Decision 3)
re-reads these two fields plus the full `turns` array via the existing
`get_session_detail_for_player` shape — no new field is added to that response either.

## No state transitions introduced

This feature adds no new persisted state machine. The "Stuck? Get a hint" control ships
disabled and holds no state at all (research.md Decision 2); nothing this feature adds
reaches the server or bears on session status.
