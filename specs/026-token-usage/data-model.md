# Data Model: Story and Session Token Usage Tracking

**Date**: 2026-09-11

**Feature**: Story and Session Token Usage Tracking (026-token-usage)

This feature adds one field to four existing entities and two fields to
their existing turn records; it introduces no new container. It also
defines one read-only, non-persisted projection — a Session Overview
Row — that the new Sessions page reads.

---

## Entity: Story (extension)

**Container**: `stories` (existing; partition key `/id`).

**New field**: `totalTokens: int = 0` — the cumulative input+output token
count of every LLM call attributable to this story's authoring lifecycle:
draft-phase world-prompt suggestions, the creation-time generation calls,
edit-time regeneration calls, the `startingPoint` backfill, and every
admin test-play exchange against this story (research.md Decisions 2, 3).
Never includes real player gameplay (Decision 4).

- Defaults to `0` for a story persisted before this field existed — no
  historical reconstruction is attempted (spec.md Assumptions).
- **Excluded from the Story Configuration File**: added to
  `story_config_file.py`'s `SYSTEM_MANAGED_KEYS`, alongside `published`,
  `createdAt`, etc. — it is operational metadata, never authored content,
  and must not round-trip through export/import.
- Only ever increases; nothing in this feature decreases it (a story
  delete removes the whole row, per 025-story-delete's existing behavior).

### Validation Rules

- `totalTokens` is never negative and is never set directly by a client —
  it only ever changes as a side effect of the LLM-call sites listed above.

---

## Entity: StoryDraft (extension)

**Container**: `storyDrafts` (existing; partition key `/id`, 24h TTL).

**New field**: `totalTokens: int = 0` — tokens spent by
`suggest_world_prompt` calls made against this draft, for both a
creation-mode draft and an edit-mode draft (`sourceStoryId` set).

### Lifecycle

- Incremented on every `suggest_world_prompt` call.
- On `generate_story` (creation): folded into the newly created `Story`'s
  `totalTokens` (research.md Decision 2) before the draft is deleted.
- On `save_draft_to_story` (edit): folded into the *existing* `Story`'s
  `totalTokens` (added, not replacing what the story already carried)
  before the draft is deleted.
- Never read or written by anything else — a draft that expires via TTL
  without converting to a story simply discards its accumulated total
  along with the rest of the draft, matching how every other in-progress
  draft field is already discarded on expiry.

---

## Entity: PlaySession (extension)

**Container**: `playSessions` (existing; partition key `/id`).

**New field**: `totalTokens: int = 0` — the running cumulative token total
across every turn and summarization call in this session (research.md
Decisions 1, 5). Never contributes to `Story.totalTokens` (Decision 4).

**New field on `PlayerInteraction`** (the turn record): `tokens: int = 0` —
that turn's own token count. `0` for turn 0 (the story's fixed opening,
replayed verbatim, no LLM call) and for a content-filtered deflection turn
(no real generation occurred).

### Validation Rules

- `PlayerInteraction.tokens` is never negative.
- `PlaySession.totalTokens` equals the sum of every turn's `tokens` plus
  every summarization call's tokens for that session — never set directly.
- **Player-facing exclusion**: `get_session_detail_for_player`'s response
  strips `tokens` from each turn dict before returning it (research.md
  Decision 6). `PlaySession.totalTokens` itself is likewise never included
  in any player-facing response — both remain admin-only, surfaced solely
  through the new Sessions page.

---

## Entity: TestPlaySession (extension)

**Container**: `testPlaySessions` (existing; partition key `/id`).

**New field**: `totalTokens: int = 0` — same running-total semantics as
`PlaySession.totalTokens`, but for an admin's test-play session. Every
qualifying exchange's tokens are added here **and** to the story's
`Story.totalTokens` (research.md Decision 3) — these are two different
totals answering two different questions, not a duplication to reconcile.

**New field on `TestPlayExchange`** (the turn record): `tokens: int = 0` —
same semantics as `PlayerInteraction.tokens`. No player-facing filtering
is needed here: the only reader of a `TestPlaySession`'s detail is the
administrator who ran it (`get_session`), and FR-013 only requires the
admin *UI* not surface it, not the API response.

---

## Read model: Session Overview Row (not persisted)

The shape the new `GET /api/manage/sessions` endpoint returns per row,
built by combining a projected read of both session containers with a
live-resolved story name and email (research.md Decisions 7):

| Field | Source |
|---|---|
| `sessionId` | `PlaySession.id` / `TestPlaySession.id` |
| `sessionType` | `"player"` / `"test"` — which container the row came from |
| `storyId` | `PlaySession.adventureId` / `TestPlaySession.storyId` |
| `storyName` | Live story-name lookup; `"(deleted story)"` if the story no longer exists |
| `totalTokens` | `PlaySession.totalTokens` / `TestPlaySession.totalTokens` |
| `email` | `ProvisionedAccountEntry.email` where `objectId` matches `playerId`/`administratorId`; `"(no longer provisioned)"` if no match |

### Validation / Display Rules

- Every session appears exactly once, regardless of `status`
  (`active`/`concluded`) — FR-018's "no recorded turns yet" case renders
  `totalTokens: 0`, not an omitted row.
- No pagination, filtering, or sorting is defined for v1 (spec.md
  Assumptions, Principle IV/XII) — the endpoint returns every row in one
  response.
