# Data Model: Story Creation

**Date**: 2026-08-29 | **Revised**: 2026-08-31 (Session 2026-08-30 Clarifications: explicit Save/Abandon/Finished, local-storage draft, blob-stored cover image)

**Feature**: Story Creation (004-story-creation)

This document defines the persisted `Story` entity this feature writes, the `Character Type` and `Completion Criteria` structures FR-008 requires as dedicated fields on it, and the purely frontend `Wizard Draft` concept that holds in-progress, unsaved wizard state before a Save.

There is no longer a server-side "StoryDraft" Cosmos entity — see research.md §7. A prior revision of this document defined one (TTL-enabled, generation-triggering); it is superseded entirely by explicit Save (FR-004) and a browser-local-storage-only draft (FR-010).

---

## Entity: Story

**Definition**: A complete (or partially complete) adventure narrative — name, optional cover image reference, outline, rules, character types, and completion criteria (spec.md Key Entities). Written to Cosmos only by an explicit administrator Save (FR-004); unpublished by default (FR-006).

**Scope**: Global; visible to administrators immediately, to players only once `005-story-publishing` marks it published.

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `id` | string (UUID) | Yes | Story identifier; also the partition key | Assigned by the backend on the first Save (create) |
| `name` | string | Yes | Story title (wizard Tab 01) | The only field required to Save at all (FR-004, FR-009) |
| `coverImageUrl` | string or null | No | Blob storage URL for an uploaded cover image (wizard Tab 01) | FR-009 — set only once a cover image has actually been uploaded via `POST /manage/stories/{storyId}/cover-image`; never a client-supplied arbitrary URL |
| `tone` | string or null | No | Narrative tone (wizard Tab 03) | No change from the original design (Clarifications: "No changes") |
| `readingLevel` | string or null | No | Target reading level (wizard Tab 03) | Same |
| `sessionLengthMinutes` | integer or null | No | Target session length (wizard Tab 04) | Same |
| `chapters` | integer or null | No | Target chapter count (wizard Tab 04) | Same |
| `outline` | string or null | No | Free-language setting/plot outline (wizard Tab 02) — editable directly, or seeded once via the one-shot "Suggest" action (FR-003) | Optional; a Story may be Saved before this is filled in |
| `rules` | string or null | No | Free-language constraints the narration must keep (wizard Tab 02), independently editable from `outline` (FR-011) | Optional |
| `characterTypes` | array of Character Type | No, may be empty | See Character Type below | No longer required to Save (unlike the superseded auto-generation design); still the dedicated field FR-008 requires when the administrator does define them |
| `completionCriteria` | Completion Criteria or null | No | See Completion Criteria below | Same relaxation as `characterTypes` |
| `published` | boolean | Yes | Defaults to `false` on creation | FR-006; flipped only by `005-story-publishing` |
| `createdBy` | string | Yes | Administrator's email address, from the authenticated admin session | FR-012 |
| `createdAt` | ISO 8601 timestamp | Yes | First Save (create) time | FR-012 |
| `updatedBy` | string | Yes | Administrator's email address who performed the most recent Save | FR-012 |
| `updatedAt` | ISO 8601 timestamp | Yes | Most recent Save time | FR-012 |
| `entityType` | string | Yes | Always `"Story"` | Container discriminator, matches existing model convention |

### Validation Rules

- `name` must be non-empty to create a Story (first Save); it cannot be cleared to empty on a later Save (update).
- `characterTypes`/`completionCriteria`, when supplied, MUST satisfy the Shared Structures below — validated server-side on every Save; the first invalid field short-circuits the whole write with a `422` (no partial merge of a rejected field alongside accepted ones in the same request), matching the prior draft-PATCH validation behavior.
- Unlike the superseded design, a Story is never required to be "complete" (non-empty outline, ≥1 character type, ≥1 completion criterion) to exist in Cosmos — Save is available and effective at any point in the wizard (FR-004).

---

## Shared Structure: Character Type

Unchanged from the original design.

| Property | Type | Required | Rationale |
|----------|------|----------|-----------|
| `name` | string | Yes | Minimum needed for `006-adventure-and-character-setup` to display a choice |
| `description` | string or null | No | Optional flavor text shown to the player alongside `name` |

---

## Shared Structure: Completion Criteria

Unchanged from the original design; shape still matches `008-core-gameplay`'s Key Entity by clarification decision.

| Property | Type | Required | Rationale |
|----------|------|----------|-----------|
| `maxDurationMinutes` | integer or null | No | Optional maximum session duration |
| `successConditions` | array of string, min length 1 when the structure is present at all | Yes (when present) | At least one win condition (SC-003) once completion criteria are defined |
| `failureConditions` | array of string | No, may be empty | Optional lose condition(s) |
| `rule` | `"any"` \| `"all"` \| null | Required only when `len(successConditions) + len(failureConditions) > 1` | How `008-core-gameplay` combines multiple conditions; omitted/null when only one condition total exists (nothing to combine) |

---

## Concept: Wizard Draft (frontend-only — not a Cosmos entity)

**Definition**: The in-progress, unsaved state of a story-creation session across all four wizard tabs, held entirely in the administrator's browser via `localStorage` (FR-010, User Story 2) under the key `llmdungeon.storyWizard.draft`. Never sent to, or held by, the backend until an explicit Save.

**Shape** (frontend-internal; not a wire contract):

```json
{
  "storyId": "9f2a... or null (null until the first Save creates the record)",
  "fields": {
    "name": "", "coverImageUrl": null,
    "tone": "", "readingLevel": "", "sessionLengthMinutes": "", "chapters": "",
    "outline": "", "rules": "", "characterTypes": [], "completionCriteria": null
  }
}
```

A pending, not-yet-uploaded cover image `File` object is held in React component state only — `File` objects are not JSON-serializable and so cannot round-trip through `localStorage`; if the browser is closed or the tab reloaded before Save, a selected-but-unsaved cover image is lost (the same "only unsaved changes are at risk" guarantee spec.md's Edge Cases already state for local storage generally).

**State transitions**:

```
Created (empty fields, storyId = null)
  → updated on every field change, any tab, any order (written to localStorage immediately)
  → [Save] → POST (storyId == null) or PATCH (storyId set) → Story upserted in Cosmos,
             storyId set from the response, fields refreshed from the persisted Story
  → [Abandon, confirmed] → DELETE the Story if storyId is set (no-op otherwise) →
             localStorage entry cleared → redirect to the main admin page
  → [Finished, confirmed] → localStorage entry cleared (nothing already saved is
             touched) → redirect to the stories list page
```

---

## Storage Model

**Container: `stories`** (Cosmos DB, existing) — partition key `/id`. No TTL. Query patterns:

```
Point read (single story): container.read_item(id=storyId, partition_key=storyId)
List (admin view): SELECT c.id, c.name, c.published, c.createdAt FROM c WHERE c.entityType = "Story"
Delete (Abandon): container.delete_item(id=storyId, partition_key=storyId)
```

**Cost**: List is a cross-partition query, acceptable at this project's small catalog scale (Principle IV — no pagination built ahead of a stated need). Provisioned by `007-azure-infrastructure-provisioning`'s Cosmos DB account (serverless, Managed Identity access via `CosmosService`, no new authentication pattern).

There is no longer a `storyDrafts` container — see research.md §7. The Cosmos-TTL-based ephemeral draft container from the original design is removed entirely; its only remaining conceptual counterpart is the frontend-only Wizard Draft above.

**Blob container: `assets`** (Azure Storage, provisioned by `007-azure-infrastructure-provisioning` for general application assets) — this feature's cover images are written under a `story-covers/{storyId}/{filename}` path prefix within that existing container (research.md §6), reached via Managed Identity (`Storage Blob Data Contributor`) over the same private-endpoint path `007` already provisions. No new blob container or Terraform change is required.
