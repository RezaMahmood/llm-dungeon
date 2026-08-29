# Feature Specification: Story Publishing

**Feature Branch**: `005-story-publishing`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: originally User Story 7 within `003-game-setup-and-authoring`, split out as its own domain because it is a small but essential, independently-testable gate. It also **resolves a direct contradiction** between the two prior source specs: `001-adventure-game` assumed a story becomes available to players automatically once creation is confirmed complete, while `003-game-setup-and-authoring` required an explicit publish step. This spec is now the single, authoritative source of truth on story visibility — the explicit publish/unpublish model wins.

**Input**: User description: "Stories/Games only become available when they are published by administrator. Story becomes available for players once published."

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), steps 05–06 (test play, publish & assign) (see [specs/designs/README.md](../designs/README.md)). The test-play gate is now specified in `017-story-publish-test-play-gate` (split out of `010-story-test-play` on 2026-08-29) and referenced below (FR-008). The screen's "assign" label has no separate functional requirement — publishing makes a story available to all players, with no targeting/assignment capability (see Assumptions). The publish/unpublish action is also reachable from the administrator's story list (`012-story-editing-and-review`), which shows each story's published/unpublished status; that screen is not yet part of the design reference prototype (see FR-010).

## Clarifications

### Session 2026-08-29

- Q: Where can an administrator actually trigger publish/unpublish for a story — only from within the story-creation/editing wizard's "Publish & assign" step, only from the "all stories" list view, or from both places? → A: Both the wizard's step 6 and the story list (`012-story-editing-and-review`) expose the same publish/unpublish action; both entry points enforce the identical FR-008 precondition, with no separate completeness check needed (an incomplete story configuration is never persisted per `004-story-creation` FR-005). When a publish attempt is blocked, the administrator MUST be shown explanatory text stating why, rather than a silent or unexplained disabled control.
- Q: Does the system need to record who published/unpublished a story and when, or is the current boolean flag sufficient? → A: Boolean flag plus a retained "last published" date/time, kept for reference (including after a later unpublish); no administrator-identity attribution is required.
- Q: Should unpublishing a story require the administrator to confirm the action first, given that it immediately removes the story from every player's adventure list? → A: Yes, via a client-side confirmation step (e.g., an "are you sure?" prompt) before the action is sent; this is a UI safeguard only, not a server-side precondition like FR-008.
- Q: Should the story list show a visible indicator for a publish-blocked story before the administrator clicks Publish, or is FR-011's post-click explanation sufficient? → A: Post-click only — no separate always-visible readiness indicator is required in the story list; FR-011's explanatory text on attempt is sufficient.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Publishes or Unpublishes a Story (Priority: P1)

An administrator controls whether a given story is visible to players by explicitly publishing it. A story created or edited by any means (guided creation, import, or editing) remains unavailable to players until this step is taken.

**Why this priority**: This is the gate that determines when work-in-progress content becomes real, player-facing content. It depends on a story already existing via story creation or import.

**Independent Test**: Create one story via either creation path, verify it does not appear in the player's adventure list, publish it, and verify it now appears; then unpublish it and verify it no longer appears to players newly starting a game.

**Acceptance Scenarios**:

1. **Given** a newly created or newly edited story, **When** it has not yet been published, **Then** it does not appear in the list of adventures a player can select.
2. **Given** an administrator publishes a story, **When** publishing completes, **Then** the story appears in the player-facing adventure list.
3. **Given** an administrator chooses to unpublish a previously published story, **When** they confirm the client-side "are you sure?" prompt, **Then** players can no longer start new games against it, but any play sessions already in progress for it are unaffected.

---

### Edge Cases

- An administrator publishes a story that is already published: the action succeeds with no effect (idempotent), not an error.
- An administrator unpublishes a story that is already unpublished: the action succeeds with no effect (idempotent), not an error.
- A player has the player-facing adventure list open at the moment a story is published or unpublished: the list reflects the change on next load/refresh, not necessarily instantaneously within an already-open view.
- A story is edited after being published (see `012-story-editing-and-review`): it remains published through the edit unless the administrator explicitly unpublishes it; editing alone does not change publish state.
- An administrator attempts to publish a story that has never been test-played, or whose content changed since its last test play: the publish action is blocked (see `017-story-publish-test-play-gate`), and the administrator sees explanatory text stating why — whether the attempt was made from the wizard or from the story list.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A story MUST default to unpublished when it is first created, regardless of whether it was created via guided creation or import.
- **FR-002**: System MUST keep an unpublished story unavailable to players in every player-facing context (adventure list, direct access) until an administrator explicitly publishes it.
- **FR-003**: System MUST allow an administrator to publish a story, making it visible and selectable in the player-facing adventure list.
- **FR-004**: System MUST allow an administrator to unpublish a previously published story, removing it from the player-facing adventure list.
- **FR-005**: Unpublishing a story MUST NOT end or otherwise affect any play session already in progress against it; it MUST only prevent new sessions from starting.
- **FR-006**: Publishing an already-published story, and unpublishing an already-unpublished story, MUST both succeed without error (idempotent).
- **FR-007**: Each distinct publishing outcome (publish an unpublished story, unpublish a published story, redundant publish, redundant unpublish, unpublish with active sessions in progress) MUST have a corresponding automated test verifying its expected behavior.
- **FR-008**: The publish action MUST be blocked unless the story has a qualifying completed test play recorded since its content was last saved (see `017-story-publish-test-play-gate`).
- **FR-009**: Publishing a story MUST NOT support targeting or restricting it to specific players or groups; once published, a story is available to every player able to reach the adventure list, with no assignment step.
- **FR-010**: The publish/unpublish action MUST be reachable both from the story-creation/editing wizard's "Publish & assign" step and from the administrator's story list (see `012-story-editing-and-review`); both entry points MUST enforce the identical FR-008 precondition, and neither MAY bypass it.
- **FR-011**: When a publish attempt is blocked by FR-008, the system MUST present the administrator with explanatory text stating why publishing is unavailable, rather than a silent or unexplained disabled control. No separate always-visible readiness indicator in the story list is required beyond this post-attempt explanation.
- **FR-012**: System MUST record the date/time a story is published, retained for reference (including after a later unpublish); it MUST NOT record which administrator performed the action.
- **FR-013**: Unpublishing a story MUST require the administrator to confirm the action via a client-side confirmation step (e.g., an "are you sure?" prompt) before the unpublish request is sent; this confirmation is a UI safeguard only and MUST NOT be enforced as a server-side precondition. Publishing MUST NOT require this confirmation step — it remains a single direct action, gated only by FR-008.

### Key Entities

- **Published Status**: A per-story flag, set only by explicit administrator action, that determines whether the story appears in the player-facing adventure list.
- **Last Published At**: A per-story timestamp recording when the story was most recently published, retained for reference even after a later unpublish. No administrator-identity attribution is recorded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unpublished stories are absent from the player-facing adventure list in testing.
- **SC-002**: Publishing a story makes it appear in the player-facing adventure list with no other change to its content.
- **SC-003**: 100% of play sessions already in progress against a story continue uninterrupted after that story is unpublished, in testing.
- **SC-004**: 100% of publish attempts against a story with no qualifying test play since its last content change are blocked in testing (see `017-story-publish-test-play-gate`).

## Assumptions

- This spec is the single source of truth for story visibility to players; `004-story-creation` and `011-story-import` both default new stories to unpublished and defer entirely to this spec for the publish/unpublish mechanism itself.
- There is no scheduled/automatic publishing (e.g., publish-at-a-future-date); publishing is always a direct, immediate administrator action.
- Only an Administrator capability (see `002-login-and-access-control`) may publish or unpublish a story; no separate approval workflow exists beyond the test-play gate in `017-story-publish-test-play-gate`.
- There is no per-player or per-group assignment/targeting capability for published stories — this was considered and explicitly excluded; "published" means available to every player, full stop.
