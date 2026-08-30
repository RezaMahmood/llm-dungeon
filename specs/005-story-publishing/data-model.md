# Data Model: Story Publishing

**Date**: 2026-08-30

**Feature**: Story Publishing (005-story-publishing)

This feature does not introduce a new entity or container. It extends the `Story` entity defined in `004-story-creation`'s `data-model.md` with the fields this spec's Key Entities (Published Status, Last Published At) and FR-008's gate require. Fields already defined by `004` are not repeated here except where their behavior changes.

---

## Entity: Story (extension)

**Container**: `stories` (existing, defined by `004-story-creation`; partition key `/id`).

### New/changed properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `published` | boolean | Yes | Already defined by `004`, defaulting to `false` at creation | FR-001, FR-002, FR-003, FR-004 — this feature is what flips it, via `publish`/`unpublish` |
| `lastPublishedAt` | ISO 8601 timestamp or null | Yes (present, nullable) | Set to "now" on every successful `publish` call (including a redundant one, research.md §2/§3); untouched by `unpublish`; `null` until first published | FR-012 — retained for reference even after a later unpublish; explicitly carries **no** administrator-identity attribution (Constitution Principle X) |
| `contentUpdatedAt` | ISO 8601 timestamp | Yes | Stamped equal to `createdAt` at creation (this feature adds the field to the creation path); updated by `012-story-editing-and-review`'s future edit path on every content-changing save | Input to the FR-008 gate check (research.md §1) — "since its content was last saved" |
| `lastTestPlayedAt` | ISO 8601 timestamp or null | Yes (present, nullable) | `null` until `017-story-publish-test-play-gate`'s future logic records a qualifying test-play exchange; this feature only reads it, never writes it | Input to the FR-008 gate check (research.md §1) |

### Publish Gate (FR-008) — derived, not stored

```
can_publish(story) = story.lastTestPlayedAt is not None
                      AND story.lastTestPlayedAt >= story.contentUpdatedAt
```

When `can_publish` is `false`, the `publish` endpoint returns a `409` (see contracts/api.md) with explanatory text (FR-011) rather than performing the write.

### State Transitions

```
published=false (default, per 004)
  → [administrator calls publish] AND [can_publish(story) is true]
      → published=true, lastPublishedAt=now()
  → [administrator calls publish] AND [can_publish(story) is false]
      → no change; 409 response with explanation (FR-011)
  → [administrator calls publish while already published=true]
      → published=true (unchanged), lastPublishedAt=now() (re-stamped, research.md §2) — idempotent (FR-006)

published=true
  → [administrator confirms unpublish] → published=false; lastPublishedAt unchanged (FR-012)
  → [administrator calls unpublish while already published=false]
      → published=false (unchanged); lastPublishedAt unchanged — idempotent (FR-006)

(any state)
  → [012's future edit path saves changed content] → contentUpdatedAt=now()
      → if this story was previously publish-gate-satisfied, it is no longer (FR-008/017 FR-003),
        with no effect on the current published boolean itself (editing doesn't change publish state,
        per spec.md Edge Cases and 017's FR-004)
```

### Validation Rules

- `publish`/`unpublish` never accept a client-supplied `published`, `lastPublishedAt`, `contentUpdatedAt`, or `lastTestPlayedAt` value — all four are server-computed, matching `004`'s existing rule that `Story` fields controlled by feature-specific business logic are never directly client-writable.
- `unpublish` has no server-side precondition beyond the story existing (FR-013 — the confirmation step is client-only).
- A `publish` call against a nonexistent `story_id` returns `404`, matching `004`'s existing `GET /api/manage/stories/{storyId}` shape.

## Storage Model

No new container. Query patterns added to the existing `stories` container (defined in `004`'s data-model.md):

```
Point read + write: container.read_item(id=storyId, partition_key=storyId) → mutate → container.replace_item(...)
```

**Cost**: ~1 RU read + ~1 RU write per publish/unpublish call — negligible at this project's scale (Principle IV).
