# Phase 1 Data Model: Core Gameplay

**Feature**: 008-core-gameplay | **Date**: 2026-09-05

## Existing entities reused (read-only)

### Story (`src/backend/models/story.py`)

This feature reads `worldPrompt`, `rules`, `characterTypes`, `completionCriteria`,
`narrativeGuidance`, `name`, `tone`, `readingLevel`, `sessionLengthMinutes`, `chapters`,
and `published` — no field is created, updated, or deleted here. `published` is
re-checked at session start (a story could be unpublished between `006`'s adventure list
and this feature's session creation).

### CompletionCriteria (`src/backend/models/story.py`)

Reused exactly as already defined (`maxDurationMinutes`, `successConditions`,
`failureConditions`, `rule`) — see research.md Decision 5 for how this feature interprets
`rule`. No change to this model.

## New Entity: Play Session

**Definition**: One player's individual playthrough of a specific published `Story` —
spec.md's "Play Session" Key Entity. Persisted so it survives across the independent HTTP
requests that make up a play session (research.md Decision 1).

**Container**: `playSessions`, partition key `/id`. No TTL (a concluded session's history
is retained; `009-save-and-continue` may later add its own resume semantics on top of
this document — out of scope here).

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Session identifier, also the partition key |
| `entityType` | string | Always `"PlaySession"` — container discriminator, matches existing convention |
| `adventureId` | string | The `Story.id` this session plays (FR-002) |
| `playerId` | string | The authenticated player's Microsoft object id (`oid`) — scopes exclusivity (FR-006) |
| `characterName` | string | Echoed from `006`'s setup (already validated there; re-validated here, see contracts) |
| `characterType` | string | Echoed from `006`'s setup |
| `status` | `"active"` \| `"concluded"` | FR-010 gate — no interaction accepted once `"concluded"` |
| `completionReason` | object or null | `{"type": "duration" \| "success" \| "failure", "detail": string \| null}` once concluded (FR-009); `null` while active. `detail` holds the matched success/failure condition text, or `null` for `"duration"` |
| `satisfiedSuccessConditions` | array of int | Indices into `Story.completionCriteria.successConditions` already satisfied (research.md Decision 6) |
| `satisfiedFailureConditions` | array of int | Indices into `Story.completionCriteria.failureConditions` already satisfied |
| `interactionInProgress` | boolean | Exclusivity/concurrency guard (research.md Decision 2) |
| `isActiveForPlayer` | boolean | True only while this is the given `playerId`'s current active session (FR-015); `submit_interaction` rejects (409) against a session where this is `false` until the player explicitly resumes it |
| `turns` | array of Player Interaction | Full narrative history, oldest first (FR-003) |
| `startedAt` | ISO 8601 timestamp | Used against `maxDurationMinutes` (research.md Decision 5) |
| `lastInteractionAt` | ISO 8601 timestamp | Used for rate limiting (research.md Decision 4) |
| `endedAt` | ISO 8601 timestamp or null | Set when `status` becomes `"concluded"` |
| `summary` | string or null | Condensed prior history, produced every 20 turns (FR-014, research.md Decision 10); `null` until the first summarization |
| `summarizedThroughTurn` | integer | `turnNumber` of the last turn folded into `summary`; `0` until first summarization |

### Validation Rules

- Created only via `POST /api/game/sessions` (contracts/api.md), which re-validates the
  same three setup fields `006-adventure-and-character-setup`'s `POST /api/game/start`
  already validates (adventure exists + published, character name non-blank ≤50 chars,
  character type valid for that adventure) — this feature does not trust a client-supplied
  "setup was already validated" claim from an earlier, separate request.
- `status` only ever transitions `"active"` → `"concluded"`, exactly once (FR-009's "record
  which condition... caused the ending" — `completionReason` is set atomically with this
  transition, never overwritten afterward).
- `turns` is append-only; no existing entry is ever edited or removed.
- Every write goes through `CosmosService` with an `if-match` ETag precondition
  (research.md Decision 2) — a failed precondition surfaces as a 409, never a silent
  overwrite.
- `summarizedThroughTurn` only ever increases, in steps of 20, and never exceeds
  `turns.length`; `summary` is only ever replaced wholesale (never appended to piecemeal)
  as part of the same write that advances `summarizedThroughTurn` (FR-014, research.md
  Decision 10).
- `isActiveForPlayer` starts `true` at creation (`POST /api/game/sessions`). Creating a
  new session, or resuming an existing one (`POST .../resume`), atomically sets that
  session's `isActiveForPlayer = true` and sets `isActiveForPlayer = false` on any other
  `playSessions` document with the same `playerId` and `status == "active"` found via a
  cross-partition query on `playerId` (FR-015) — a concluded session's `isActiveForPlayer`
  value is left as-is and is never checked. At most one `status == "active"` session per
  `playerId` may have `isActiveForPlayer == true` at any time.

### State Transitions

```
Created (status="active", turns=[opening narrative], entityType="PlaySession",
         isActiveForPlayer=true; any other active session of this playerId set
         isActiveForPlayer=false)
  → each POST .../interactions:
      - reject (423) if the player's Player Content-Safety Standing is locked out
      - reject (409) if status == "concluded"
      - reject (409) session_inactive if isActiveForPlayer == false (FR-015) — the
        player must POST .../resume first
      - reject (429) if now - lastInteractionAt < MIN_INTERACTION_INTERVAL_SECONDS
      - reject (409) if interactionInProgress or ETag precondition fails
      - duration ceiling reached → status="concluded", completionReason={"type":"duration"}
      - else: LLM turn generated (in-fiction guardrail, research.md Decision 8) →
        satisfied-condition sets updated → any/all rule evaluated (research.md
        Decisions 5-6) → status="concluded" with
        completionReason={"type":"success"|"failure", detail:...} if triggered
      - if turns.length is now a multiple of 20: summarize (research.md Decision 10) →
        summary/summarizedThroughTurn updated in the same write
      - if the input or output was content-filtered: Player Content-Safety Standing
        flaggedCount incremented (research.md Decision 9), narrative replaced with the
        safe in-fiction deflection
  → [status == "concluded"] → no further interaction accepted (FR-010)

  → POST .../resume (FR-015, only meaningful while status == "active"):
      - reject (403) if playerId != authenticated user
      - reject (409) if isActiveForPlayer already true (nothing to resume)
      - else: set isActiveForPlayer=true on this session, isActiveForPlayer=false on any
        other active session of this playerId
```

## New Structure: Player Interaction (embedded in `PlaySession.turns`)

Not a top-level Cosmos document — spec.md's "Player Interaction" Key Entity, stored only
inside its parent session (mirrors `Story-Creation Exchange`'s embedding pattern in
`004-story-creation-done`).

| Field | Type | Notes |
|---|---|---|
| `turnNumber` | integer | 0 for the opening narrative (no player input), 1+ thereafter |
| `playerInput` | string or null | `null` for the opening narrative; the player's free-text action otherwise |
| `narrativeText` | string | The system's narrative response; no longer than 150 words (FR-002, research.md Decision 6a) and MUST NOT contradict prior `turns`/`summary` (FR-003, research.md Decision 6a) |
| `suggestedActions` | array of string | 2-3 alternative actions offered alongside free text (UI Design System Requirements: "Suggested actions MUST always be available") |
| `locationLabel` | string | Status-panel "Where you are" (Screen Contracts: Play surface) |
| `goalLabel` | string or null | Status-panel "Your goal" |
| `progress` | object or null | `{"current": int, "total": int}` when `Story.chapters` is set, else `null` (progress bar is only meaningful when a target chapter count exists) |
| `timestamp` | ISO 8601 timestamp | Ordering within the session |

## New Entity: Player Content-Safety Standing

**Definition**: spec.md's "Player Content-Safety Standing" Key Entity — a per-player,
cross-session record of accumulated content-safety-flagged submissions and any resulting
lockout (FR-013, research.md Decision 9).

**Container**: `playerContentSafetyStandings`, partition key `/id`, where `id == playerId`
(the same Entra `oid` used as `PlaySession.playerId`).

| Field | Type | Notes |
|---|---|---|
| `id` | string | The player's `oid` — also the partition key |
| `entityType` | string | Always `"PlayerContentSafetyStanding"` |
| `flaggedCount` | integer | Total content-safety-flagged submissions across all of this player's sessions/adventures; never reset |
| `lockoutUntil` | ISO 8601 timestamp or null | Set to `now + 1 hour` when `flaggedCount` reaches 3; a later flagged submission arriving after that lockout has expired resets `lockoutUntil` to a fresh `now + 1 hour` (this can only happen once the prior lockout has expired, since both endpoints reject with 423 — before any LLM call, and therefore before any flag can be recorded — while `lockoutUntil` is still in the future); `null` if never locked out |

### Validation Rules

- Created lazily (first flagged submission for a player) rather than pre-provisioned.
- `flaggedCount` only ever increments, by exactly 1 per flagged submission (input or
  output), via a conditional (`if-match`) write.
- Checked by both `POST /api/game/sessions` and `POST .../interactions` before any LLM
  call; `lockoutUntil` in the future → 423 (contracts/api.md), regardless of which
  session/adventure the player is trying to use.

## New Entity: Session Summary

**Definition**: spec.md's "Session Summary" Key Entity — not a standalone document, but
the `summary`/`summarizedThroughTurn` fields on its parent `PlaySession` (research.md
Decision 10), listed separately here because spec.md calls it out as its own Key Entity.
Produced every 20 turns; used as prior narrative-generation context from the next turn
onward; explicitly not a save-point/checkpoint mechanism (spec.md Assumptions).

See `PlaySession.summary` / `PlaySession.summarizedThroughTurn` above for fields and the
State Transitions diagram above for when it is (re)computed.

## Storage Model

**Container: `playSessions`** — partition key `/id`. Query patterns:

```
Point read: container.read_item(id=sessionId, partition_key=sessionId)
Conditional write: container.replace_item(item, if_match_etag=...)
```

**Cost**: ~1 RU per read; write cost grows with `turns` length, bounded in practice by one
session's configured `maxDurationMinutes`/typical play length (Principle IV — no
pagination or history-trimming built ahead of a stated need).

Provisioned by `007-azure-infrastructure-provisioning`'s existing Cosmos DB account
(serverless, Managed Identity access via `CosmosService`) — a new
`azurerm_cosmosdb_sql_container` resource, no new role assignment needed (the Function
App's Managed Identity already holds the Cosmos DB Built-in Data Contributor role at the
account scope).

**Container: `playerContentSafetyStandings`** — partition key `/id`. Query patterns:

```
Point read: container.read_item(id=playerId, partition_key=playerId)
Conditional write: container.replace_item(item, if_match_etag=...) or create_item on first flag
```

**Cost**: ~1 RU per read/write; documents are tiny and fixed-size (Principle IV — no
growth concern). Provisioned the same way as `playSessions` above — a second new
`azurerm_cosmosdb_sql_container` resource, no new role assignment.
