# Feature Specification: Story Publishing

**Feature Branch**: `005-story-publishing`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: originally User Story 7 within `003-game-setup-and-authoring`, split out as its own domain because it is a small but essential, independently-testable gate. It also **resolves a direct contradiction** between the two prior source specs: `001-adventure-game` assumed a story becomes available to players automatically once creation is confirmed complete, while `003-game-setup-and-authoring` required an explicit publish step. This spec is now the single, authoritative source of truth on story visibility — the explicit publish/unpublish model wins.

**Input**: User description: "Stories/Games only become available when they are published by administrator. Story becomes available for players once published."

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), steps 05–06 (test play, publish & assign) (see [specs/designs/README.md](../designs/README.md)). The test-play gate is now specified in `010-story-test-play` and referenced below (FR-008). The screen's "assign" label has no separate functional requirement — publishing makes a story available to all players, with no targeting/assignment capability (see Assumptions).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Publishes or Unpublishes a Story (Priority: P1)

An administrator controls whether a given story is visible to players by explicitly publishing it. A story created or edited by any means (guided creation, import, or editing) remains unavailable to players until this step is taken.

**Why this priority**: This is the gate that determines when work-in-progress content becomes real, player-facing content. It depends on a story already existing via story creation or import.

**Independent Test**: Create one story via either creation path, verify it does not appear in the player's adventure list, publish it, and verify it now appears; then unpublish it and verify it no longer appears to players newly starting a game.

**Acceptance Scenarios**:

1. **Given** a newly created or newly edited story, **When** it has not yet been published, **Then** it does not appear in the list of adventures a player can select.
2. **Given** an administrator publishes a story, **When** publishing completes, **Then** the story appears in the player-facing adventure list.
3. **Given** an administrator unpublishes a previously published story, **When** unpublishing completes, **Then** players can no longer start new games against it, but any play sessions already in progress for it are unaffected.

---

### Edge Cases

- An administrator publishes a story that is already published: the action succeeds with no effect (idempotent), not an error.
- An administrator unpublishes a story that is already unpublished: the action succeeds with no effect (idempotent), not an error.
- A player has the player-facing adventure list open at the moment a story is published or unpublished: the list reflects the change on next load/refresh, not necessarily instantaneously within an already-open view.
- A story is edited after being published (see `012-story-editing-and-review`): it remains published through the edit unless the administrator explicitly unpublishes it; editing alone does not change publish state.
- An administrator attempts to publish a story that has never been test-played, or whose content changed since its last test play: the publish action is blocked (see `010-story-test-play`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A story MUST default to unpublished when it is first created, regardless of whether it was created via guided creation or import.
- **FR-002**: System MUST keep an unpublished story unavailable to players in every player-facing context (adventure list, direct access) until an administrator explicitly publishes it.
- **FR-003**: System MUST allow an administrator to publish a story, making it visible and selectable in the player-facing adventure list.
- **FR-004**: System MUST allow an administrator to unpublish a previously published story, removing it from the player-facing adventure list.
- **FR-005**: Unpublishing a story MUST NOT end or otherwise affect any play session already in progress against it; it MUST only prevent new sessions from starting.
- **FR-006**: Publishing an already-published story, and unpublishing an already-unpublished story, MUST both succeed without error (idempotent).
- **FR-007**: Each distinct publishing outcome (publish an unpublished story, unpublish a published story, redundant publish, redundant unpublish, unpublish with active sessions in progress) MUST have a corresponding automated test verifying its expected behavior.
- **FR-008**: The publish action MUST be blocked unless the story has a qualifying completed test play recorded since its content was last saved (see `010-story-test-play`).
- **FR-009**: Publishing a story MUST NOT support targeting or restricting it to specific players or groups; once published, a story is available to every player able to reach the adventure list, with no assignment step.

### Key Entities

- **Published Status**: A per-story flag, set only by explicit administrator action, that determines whether the story appears in the player-facing adventure list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unpublished stories are absent from the player-facing adventure list in testing.
- **SC-002**: Publishing a story makes it appear in the player-facing adventure list with no other change to its content.
- **SC-003**: 100% of play sessions already in progress against a story continue uninterrupted after that story is unpublished, in testing.
- **SC-004**: 100% of publish attempts against a story with no qualifying test play since its last content change are blocked in testing (see `010-story-test-play`).

## Assumptions

- This spec is the single source of truth for story visibility to players; `004-story-creation` and `011-story-import` both default new stories to unpublished and defer entirely to this spec for the publish/unpublish mechanism itself.
- There is no scheduled/automatic publishing (e.g., publish-at-a-future-date); publishing is always a direct, immediate administrator action.
- Only an Administrator capability (see `002-login-and-access-control`) may publish or unpublish a story; no separate approval workflow exists beyond the test-play gate in `010-story-test-play`.
- There is no per-player or per-group assignment/targeting capability for published stories — this was considered and explicitly excluded; "published" means available to every player, full stop.
