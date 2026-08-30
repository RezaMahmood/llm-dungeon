# Research: Story Publishing

**Date**: 2026-08-30

**Feature**: Story Publishing (005-story-publishing)

No item in this plan's Technical Context is marked `NEEDS CLARIFICATION` — the spec's own Clarifications session already resolved the four open questions that would otherwise require research (entry points, attribution, unpublish confirmation, readiness-indicator scope). The items below instead record the design decisions needed to turn FR-008/FR-012/FR-013 into concrete field/endpoint shapes.

## 1. How does the FR-008 test-play gate check work before `017-story-publish-test-play-gate` exists?

**Decision**: Add two fields to the `Story` document — `contentUpdatedAt` (ISO 8601, stamped at creation and on every future content-changing save) and `lastTestPlayedAt` (ISO 8601 or null, written only by `017`'s future test-play-exchange logic). The publish gate is a pure read-side check: `lastTestPlayedAt is not None and lastTestPlayedAt >= contentUpdatedAt`.

**Rationale**: This is the minimal shared state the two features need. `005` does not need to know *how* a qualifying test-play exchange is detected (that's `017`'s FR-001) — only whether one has happened since the content was last saved. Until `017` ships, `lastTestPlayedAt` stays `null` on every story, so the gate check correctly blocks every publish attempt — this is the spec-correct behavior for a story that has genuinely never been test-played, not a workaround.

**Alternatives considered**:
- *Have `005` also implement `017`'s tracking logic now*: rejected — out of scope for this spec, duplicates work `017`'s own plan will do, and couples two independently-planned features.
- *Skip the gate entirely until `017` lands*: rejected — FR-008 is a MUST requirement of this spec; shipping publish without any gate would need to be un-shipped later, and the two-field interface above costs nothing extra now.

## 2. Where does `lastPublishedAt` (FR-012) live, and how does it interact with unpublish?

**Decision**: A single nullable `lastPublishedAt` (ISO 8601) field on `Story`, set on every successful publish (including a redundant publish per FR-006 — re-stamping to "now" is harmless and simpler than special-casing "unchanged if already published"), and left untouched by unpublish.

**Rationale**: FR-012 requires the timestamp to be "retained for reference (including after a later unpublish)" — unpublish must not clear it. Re-stamping on a redundant publish keeps the semantics simple ("last time this story was made live") without needing to detect "was this a no-op transition."

**Alternatives considered**:
- *Only stamp on the 0→1 transition, leave it untouched on a redundant publish*: rejected — adds a branch for no behavioral benefit; the spec only requires the value be "the most recently published" time, which re-stamping satisfies identically.

## 3. Idempotency implementation (FR-006)

**Decision**: `publish(story_id)` and `unpublish(story_id)` are unconditional writes — set `published = True` (or `False`) and, for publish, `lastPublishedAt = now()` — with no pre-check comparing against the current value. Cosmos's point-write is already atomic per document; no optimistic-concurrency (`etag`) handling is needed beyond what `story_service.py`'s existing read-modify-write pattern (established in `004`) already does.

**Rationale**: An unconditional write is trivially idempotent and simpler than branching on current state (Principle IV). The one exception is the FR-008 gate check, which still runs on every publish call (including a redundant one) — a story cannot become un-gated by having once passed the gate.

**Alternatives considered**:
- *Short-circuit if already in the target state*: rejected — no observable behavioral difference, and skips the FR-012 re-stamp decision made in §2.

## 4. Unpublish confirmation (FR-013) — client-only, no server precondition

**Decision**: The confirmation prompt is implemented entirely in `StepPublish.jsx` (a simple "Are you sure? Unpublishing removes this story from every player's adventure list." dialog using the design system's existing confirmation/dialog primitive) before `storyDraftService.unpublishStory` is even called. The backend `unpublish` endpoint has no separate "confirmed" flag or precondition.

**Rationale**: The spec is explicit that this is "a UI safeguard only, not a server-side precondition." Adding a server-side confirmation token would be unused complexity (Principle IV) and would contradict the spec's own framing.

## 5. Reachability from `012-story-editing-and-review`'s story list (FR-010)

**Decision**: This plan builds the `publish`/`unpublish` endpoints and the wizard's `StepPublish.jsx` entry point only. It does not build a story-list page — `012`'s spec note confirms that screen "is not yet part of the design reference prototype" and is `012`'s own scope. `012`'s future plan will call the same two endpoints this feature adds, satisfying FR-010's "both entry points enforce the identical FR-008 precondition" requirement by construction (one shared backend check, two callers).

**Rationale**: Building a placeholder story-list screen here would duplicate `012`'s eventual work and risks drifting from `012`'s own design once it's planned. FR-010 only requires that *both* entry points exist and enforce the same precondition — it does not require this feature to build both UIs.
