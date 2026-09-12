# Data Model: Story Test Play

**Feature**: `010-story-test-play` | **Date**: 2026-09-08

Entities this feature proposes to create are marked **(proposed)**; everything else was
read from `origin/main`.

## TestPlaySession **(proposed)**

Container `testPlaySessions` **(proposed)**, partition key `/id`. Mirrors the shape of
`PlaySession` (`src/backend/models/play_session.py`) so the shared turn and completion
logic applies unchanged, minus the player-only concerns (checkpoints, `isActiveForPlayer`,
autosave/resume).

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Cosmos id and partition key |
| `storyId` | `str` | The story under test. Named `storyId`, not `adventureId` — a draft story is not an adventure |
| `administratorId` | `str` | The admin's `oid`. Named distinctly from `playerId` so no player query can match it |
| `characterName` | `str` | Fixed literal `"Tester"` (research Decision 6) |
| `characterType` | `str` | First entry of `story.characterTypes` |
| `status` | `str` | `"active"` or `"concluded"`, matching `PlaySession`'s two values |
| `completionReason` | `dict \| None` | `{"type": "success"｜"failure"｜"duration", "detail": str｜None}` |
| `satisfiedSuccessConditions` | `list[int]` | Indices into `story.completionCriteria.successConditions` |
| `satisfiedFailureConditions` | `list[int]` | Indices into `story.completionCriteria.failureConditions` |
| `interactionInProgress` | `bool` | Single-flight claim, enforced with `_etag` + `MatchConditions.IfNotModified` |
| `turns` | `list[TestPlayExchange]` | Turn 0 is the opening narrative |
| `startedAt` | `str` | `"%Y-%m-%dT%H:%M:%SZ"` |
| `lastInteractionAt` | `str` | Backs the 2-second interval check |
| `endedAt` | `str \| None` | Set when `status` becomes `"concluded"` |
| `summary` | `str \| None` | Rolling summary, as `PlaySession` |
| `summarizedThroughTurn` | `int` | Default `0` |
| `entityType` | `str` | `"TestPlaySession"` |

**Deliberately absent**: `checkpoints` and `isActiveForPlayer`. Test play has no
save/continue behavior (`009-save-and-continue` is scoped to real players per this
spec's Assumptions), and per-player session exclusivity is an interference vector
(research Decision 3).

**State transitions**: `active → concluded` on a turn whose completion evaluation
returns non-`None` (FR-004). `active → deleted` on abort (FR-005) — a hard delete, not a
status value, so no tombstone survives. There is no `concluded → active` transition;
test play has no resume.

## TestPlayExchange **(proposed)**

An element of `TestPlaySession.turns`; the spec's **Test Play Exchange** entity. Same
shape as `PlayerInteraction`.

| Field | Type | Notes |
|---|---|---|
| `turnNumber` | `int` | 0 is the opening narrative |
| `narrativeText` | `str` | |
| `suggestedActions` | `list[str]` | |
| `locationLabel` | `str` | |
| `timestamp` | `str` | |
| `playerInput` | `str \| None` | `None` on turn 0 — which is why turn 0 is not a qualifying exchange (research Decision 9) |
| `goalLabel` | `str \| None` | |
| `progress` | `dict[str, int] \| None` | |

**Qualifying exchange**: `playerInput is not None` and the turn persisted successfully.
Only such a turn writes `Story.lastTestPlayedAt`.

## Story (existing — one write path added)

`src/backend/models/story.py`. No schema change: every field this feature needs already
exists.

| Field | Existing behavior | This feature |
|---|---|---|
| `lastTestPlayedAt` | Declared, serialized, compared in `can_publish()`, carried across content writes — never written | **Written** on each qualifying exchange **(proposed write path)** |
| `contentUpdatedAt` | Stamped `_now()` on every content write | Untouched — writing the marker must not re-arm the gate |
| `published`, `lastPublishedAt` | Set by `publish()`/`unpublish()` | Unchanged; FR-007 calls the existing publish action |

`can_publish()` remains `lastTestPlayedAt is not None and lastTestPlayedAt >= contentUpdatedAt`.
Supplying the writer is what makes it satisfiable for the first time.

## Relationships

```text
Story ──1:N── TestPlaySession        (storyId; no back-reference on Story)
  │
  └── lastTestPlayedAt ◄── stamped by a qualifying TestPlayExchange
                            (survives its session's deletion — FR-010)

TestPlaySession ──1:N── TestPlayExchange   (embedded in turns)
```

The Story carries no reference to its test sessions, so deleting a session (FR-005) is a
single-document delete that cannot disturb the marker.

## Validation rules

- A test-play session may only be created against a story the administrator can read;
  unlike real play, `story.published` is **not** required — testing a draft is the point.
- `characterType` must name an entry of `story.characterTypes`; `Story.__post_init__`
  already guarantees at least one exists.
- An empty or whitespace-only instruction is rejected before any LLM call, as
  `submit_interaction` does.
- Completion is evaluated only for turns with `playerInput is not None`.
- A story with no reachable ending still accepts exchanges; abort is then the only exit
  (spec Edge Cases).

## Isolation invariants (FR-009)

1. `TestPlaySession` documents live in `testPlaySessions`; no `game/*` route reads that
   container.
2. `administratorId` never appears in a player query, all of which filter on `playerId`.
3. No test-play write touches `playSessions` or `playerContentSafetyStandings`.
4. The only shared mutable state is `Story.lastTestPlayedAt`, which is
   administrator-facing and read solely by the publish gate.
