# Data Model: Story Creation

**Date**: 2026-08-29

**Feature**: Story Creation (004-story-creation)

This document defines the entities this feature introduces: an ephemeral `StoryDraft` (the in-progress wizard/conversation session) and the persisted `Story` it produces, along with the `Character Type` and `Completion Criteria` structures FR-008 requires as dedicated fields on both.

---

## Entity: Story Draft

**Definition**: The in-progress state of one story-creation session — the wizard's structured field values plus the guiding-question conversation history — before enough detail exists to generate and persist a `Story`. Never visible to players; never itself a playable/catalog entry (see research.md §3).

**Scope**: Owned by the administrator who started it. Multiple concurrent drafts per administrator are permitted (Clarifications).

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `id` | string (UUID) | Yes | Draft identifier; also the partition key | One document per session |
| `createdBy` | string | Yes | Administrator's Microsoft object id (`oid`) | Scopes the draft to its owner |
| `name` | string or null | No | Story title (wizard step "Name & cover") | Required (non-empty) before generation can trigger (revised 2026-08-31) |
| `coverImageUrl` | string or null | No | Cover image reference (wizard step "Name & cover") | Optional; not required for completeness. **Open question (flagged 2026-08-30, see spec.md § Open Questions)**: what this string is meant to contain — an externally-hosted image link, an uploaded/managed asset reference, or something else — is not yet specified. |
| `tone` | string or null | No | Narrative tone (wizard step "Tone & reading level") | Optional until generation |
| `readingLevel` | string or null | No | Target reading level (wizard step "Tone & reading level") | Optional until generation |
| `sessionLengthMinutes` | integer or null | No | Target session length (wizard step "Session length") | Optional until generation |
| `chapters` | integer or null | No | Target chapter count (wizard step "Session length") | Optional until generation |
| `worldPrompt` | string or null | No | Free-language setting/plot description (FR-001, FR-002) | Required (non-empty) before generation can trigger |
| `rules` | string or null | No | Free-language constraints the narration must keep | Optional |
| `characterTypes` | array of Character Type | Yes, may be empty | See Character Type below | At least one required before generation can trigger (FR-008) |
| `completionCriteria` | Completion Criteria or null | No | See Completion Criteria below | Required (non-null, ≥1 success condition) before generation can trigger (FR-008) |
| `createdAt` | ISO 8601 timestamp | Yes | Session start time | Audit/debugging |
| `updatedAt` | ISO 8601 timestamp | Yes | Last write time | Drives the TTL refresh (research.md §3) |
| `ttl` | integer (seconds) | Yes | Cosmos TTL, reset to 86400 on every update | Auto-expires an abandoned draft (FR-005) — see research.md §3 |
| `entityType` | string | Yes | Always `"StoryDraft"` | Container discriminator, matches existing model convention |

### Completeness Rule (unlocks generation — FR-003/FR-004)

A draft is complete — meaning the explicit `POST .../generate` action (contracts/api.md) is available — when all of:
- `name` is non-empty, AND
- `worldPrompt` is non-empty, AND
- `characterTypes` has at least one entry, AND
- `completionCriteria` is non-null and has at least one entry in `successConditions`.

(`name` added 2026-08-31 — a story must have a title to be generated, not just narrative content.)

Every `PATCH`/message write re-evaluates and reports this as `readyToGenerate`, but generation itself never happens as a side effect of that write — it is a separate, administrator-triggered action (revised 2026-08-31, #33: auto-generating on whichever write happened to complete the draft caused the wizard to redirect away mid-edit, on an ordinary field blur, with no warning).

### State Transitions

```
Created (empty fields, entityType="StoryDraft")
  → updated repeatedly via PATCH / world-prompt suggestion (any order, any number of times)
  → [Completeness Rule met] → readyToGenerate: true reported, draft otherwise unchanged
  → [administrator explicitly calls POST .../generate] → Story generated and persisted → draft document deleted
  → [administrator stops interacting] → ttl expires → draft document deleted (never became a Story)
```

A draft is never directly deleted by an explicit "abandon" action (Assumptions: no resume requirement, so no abandon UI is needed either — TTL is the only exit path besides successful generation).

---

## Entity: Story

**Definition**: A complete adventure narrative — setting, character types, plot, and completion criteria — along with the guidance needed to keep the LLM's later narration consistent with it (spec.md Key Entities). Created only by successful generation from a complete `StoryDraft`; unpublished by default (FR-006).

**Scope**: Global; visible to administrators immediately, to players only once `005-story-publishing-done` marks it published.

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `id` | string (UUID) | Yes | Story identifier; also the partition key | |
| `name` | string or null | No | Carried over from the draft | Deferred as a formal Key Entity attribute (Clarifications) but still stored — the wizard collects it and the design's story-select/catalog screens display it |
| `coverImageUrl` | string or null | No | Carried over from the draft | Same deferral as `name` |
| `tone` | string or null | No | Carried over from the draft | Deferred (Clarifications) |
| `readingLevel` | string or null | No | Carried over from the draft | Deferred (Clarifications) |
| `sessionLengthMinutes` | integer or null | No | Carried over from the draft | Deferred (Clarifications) |
| `chapters` | integer or null | No | Carried over from the draft | Deferred (Clarifications) |
| `worldPrompt` | string | Yes | The administrator's setting/plot description | Required input to generation |
| `rules` | string or null | No | The administrator's constraints | Optional input to generation |
| `characterTypes` | array of Character Type | Yes, min length 1 | See below | FR-008, SC-003 |
| `completionCriteria` | Completion Criteria | Yes, min 1 success condition | See below | FR-008, SC-003; shape matches `008-core-gameplay-done`'s Key Entity |
| `narrativeGuidance` | string | Yes | LLM-generated prose the play-session narrator (`008-core-gameplay-done`) uses to stay consistent with this story | The "guidance... to keep the LLM's later narration consistent" named in spec.md's Story Key Entity |
| `startingPoint` | Starting Point | Yes (from 2026-09-08, #271) | LLM-generated from `narrativeGuidance` at generation time; replayed verbatim as turn 0 of every session (`008-core-gameplay-done`) | A story's opening is fixed and admin-reviewable, not regenerated per session (#271) |
| `published` | boolean | Yes | Defaults to `false` on creation | FR-006; flipped only by `005-story-publishing-done` |
| `createdBy` | string | Yes | Administrator's `oid` | Audit trail |
| `createdAt` | ISO 8601 timestamp | Yes | Generation time | Audit trail |
| `entityType` | string | Yes | Always `"Story"` | Container discriminator |

### Validation Rules

- A `Story` is only ever created by the backend's generation step, never directly via a client-supplied write — enforces FR-003 (LLM-generated) and FR-004 (auto-persisted as one atomic step).
- `characterTypes` and `completionCriteria` MUST satisfy the same minimums as the draft's Completeness Rule — re-validated server-side at generation time even though the draft's own writes already enforce it, since the LLM's own output (`narrativeGuidance`) is what's actually new and unvalidated at that point (Edge Cases: malformed LLM output must not be persisted).
- If either Foundry call — `narrativeGuidance`, or the `startingPoint` generated from it — fails or returns content that fails validation (empty, or not parseable per research.md §4's schemas), no `Story` is written and the draft is left intact for another attempt (Edge Cases).
- `startingPoint` is `null` only on a `Story` row persisted before 2026-09-08 (#271); such a row is backfilled on its next session start (`008-core-gameplay-done` data-model.md).

---

## Shared Structure: Starting Point

Added 2026-09-08 (#271). Embedded in `Story.startingPoint`; carries exactly the fields a
`008-core-gameplay-done` Player Interaction does, minus the per-session ones
(`turnNumber`, `playerInput`, `timestamp`).

| Property | Type | Required | Rationale |
|----------|------|----------|-----------|
| `narrativeText` | string | Yes | The opening narrative every player sees; same 150-word ceiling as a turn |
| `suggestedActions` | array of string, min length 1 | Yes | Suggested actions must be available on every turn, turn 0 included |
| `locationLabel` | string | Yes | Status-panel "Where you are" at turn 0 |
| `goalLabel` | string or null | No | Status-panel "Your goal" at turn 0 |
| `progress` | object or null | No | `{"current": int, "total": int}` when `chapters` is set |

Written without reference to any character name or type — it is identical for every player
of the story.

---

## Shared Structure: Character Type

Used identically inside `StoryDraft.characterTypes` and `Story.characterTypes`.

| Property | Type | Required | Rationale |
|----------|------|----------|-----------|
| `name` | string | Yes | Minimum needed for `006-adventure-and-character-setup` to display a choice |
| `description` | string or null | No | Optional flavor text shown to the player alongside `name` |

---

## Shared Structure: Completion Criteria

Used identically inside `StoryDraft.completionCriteria` and `Story.completionCriteria`. Shape matches `008-core-gameplay-done`'s Key Entity by clarification decision.

| Property | Type | Required | Rationale |
|----------|------|----------|-----------|
| `maxDurationMinutes` | integer or null | No | Optional maximum session duration |
| `successConditions` | array of string, min length 1 | Yes | At least one win condition (SC-003) |
| `failureConditions` | array of string | No, may be empty | Optional lose condition(s) |
| `rule` | `"any"` \| `"all"` \| null | Required only when `len(successConditions) + len(failureConditions) > 1` | How `008-core-gameplay-done` combines multiple conditions; omitted/null when only one condition total exists (nothing to combine) |

---

## Entity: Story-Creation Exchange (removed 2026-09-08, #227)

**Amendment (2026-09-08, #227)**: The guided, multi-turn conversation this entity recorded is gone. Sending an idea from the wizard's "World & setting" step is now a single pass: the idea goes to the model exactly once, and the one thing that comes back — a suggested `worldPrompt` — is written to that field and surfaced nowhere else. With no conversation to replay, `StoryDraft.exchanges` and the `StoryCreationExchange` entity were removed rather than left as a permanently empty array. Drafts persisted before this change still load: `StoryDraft.from_dict` reads the fields it knows and ignores a stored `exchanges` array.

---

## Storage Model

**Container: `storyDrafts`** — partition key `/id`. TTL enabled per-item (research.md §3). Query patterns:

```
Point read: container.read_item(id=draftId, partition_key=draftId)
```
**Cost**: ~1 RU per read; a draft is a small, bounded document (its largest fields are `worldPrompt`/`rules` free text), so writes stay at a few RU regardless of how many times it is edited.

**Container: `stories`** — partition key `/id`. No TTL. Query patterns:

```
Point read (single story): container.read_item(id=storyId, partition_key=storyId)
List (admin view): SELECT * FROM c WHERE c.entityType = "Story"
```
**Cost**: List is a cross-partition query, acceptable at this project's small catalog scale (Principle IV — no pagination built ahead of a stated need).

Both containers are provisioned by `007-azure-infrastructure-provisioning`'s Cosmos DB account (serverless, Managed Identity access via `CosmosService`, no new authentication pattern).
