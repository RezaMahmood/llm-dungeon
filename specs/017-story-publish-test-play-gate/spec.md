# Feature Specification: Story Publish Test-Play Gate

**Feature Branch**: `017-story-publish-test-play-gate`

**Created**: 2026-08-29

**Status**: Draft

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), step 05 "Test play" / step 06 "Publish" (see [specs/designs/README.md](../designs/README.md))

**Input**: Split out of `010-story-test-play` on 2026-08-29, so that spec covers at most two user stories. This spec covers the third user story originally specified there — "A Story Cannot Be Published Without a Completed Test Play" — along with the "no assignment requirement" constraint on publishing that originally accompanied it, per the same user instruction: "there should be no 'assignment' requirement - once the story is published then it is available to all."

**Split**: This spec depends on `010-story-test-play` for the Test Play Exchange concept it gates on, and on `005-story-publishing` for the publish action it blocks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Story Cannot Be Published Without a Completed Test Play (Priority: P1)

The publish action (see `005-story-publishing`) is blocked until the story has had at least one test-play exchange since its content was last changed.

**Why this priority**: This is what makes test play meaningful rather than optional busywork. It depends on both `010-story-test-play` (test play exists) and `005-story-publishing` (a publish action exists to gate).

**Independent Test**: Attempt to publish a brand-new draft story that has never been test-played and verify it is blocked; perform one test-play exchange, then verify publish succeeds; edit the story's content again and verify publish is blocked again until another test-play exchange occurs.

**Acceptance Scenarios**:

1. **Given** a draft story that has never been test-played, **When** an administrator attempts to publish it, **Then** the system blocks the publish action and indicates a test play is required first.
2. **Given** a draft story that has had at least one test-play exchange since its content was last saved, **When** an administrator attempts to publish it, **Then** the publish action is allowed to proceed.
3. **Given** a story that previously had a qualifying test play, **When** its content (e.g., world prompt, character types, completion criteria) is changed and saved again, **Then** the test-play requirement is reset, and publishing is blocked again until a new test-play exchange occurs against the updated content.
4. **Given** a story that is already published, **When** an administrator edits its content, **Then** the edit takes effect immediately without requiring a new test play, consistent with existing story-editing behavior (see `012-story-editing-and-review`); the test-play gate applies only to the publish action itself, not to edits of an already-published story.
5. **Given** an administrator starts a test-play session but takes no actions before leaving, **When** they later attempt to publish, **Then** the publish action remains blocked, since no test-play exchange occurred.

---

### Edge Cases

- An administrator publishes a story, then edits its content while players are mid-session: this spec does not change that existing behavior (see `012-story-editing-and-review`) — the test-play gate does not apply, since the story is already published.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track, per story, whether at least one test-play exchange (a submitted test instruction and its resulting response, per `010-story-test-play`) has occurred since that story's content was last saved.
- **FR-002**: The publish action defined in `005-story-publishing` MUST be blocked, with a clear explanation, unless the story has at least one test-play exchange recorded since its content was last saved.
- **FR-003**: Saving a change to a story's content MUST reset its recorded test-play status, so a previously satisfied publish gate does not carry over to changed content.
- **FR-004**: The test-play gate applies only to the publish action; it MUST NOT block or otherwise affect edits to a story that is already published (see `012-story-editing-and-review`).
- **FR-005**: Publishing a story MUST NOT include, or depend on, any capability to target or restrict it to specific players or groups — once published, a story is available to every player able to reach the adventure list, with no assignment step (see `005-story-publishing`).
- **FR-006**: Each distinct gate outcome (publish blocked with no test play, publish allowed after a qualifying test play, publish blocked again after a content change) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Test-Play Status**: Per-story state tracking whether a qualifying Test Play Exchange (`010-story-test-play`) has occurred since the story's content was last saved; the sole input to this spec's publish gate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of publish attempts against a story with no qualifying test-play exchange since its last content change are blocked in testing.
- **SC-002**: 100% of publish attempts against a story with a qualifying test-play exchange since its last content change succeed (assuming no other publish requirement is violated) in testing.
- **SC-003**: 100% of content changes to a story in testing reset its test-play status, requiring a new qualifying exchange before the next publish attempt.

## Assumptions

- "Completed a test play" means at least one test-play exchange (a submitted instruction and its response, per `010-story-test-play`) has occurred against the story's current saved content — not necessarily a full playthrough to one of the story's own ending conditions. This is testing/QA in spirit, not a requirement to fully complete the adventure.
- The test-play gate applies only to the transition from unpublished to published (the publish action itself, per `005-story-publishing`); it does not apply to ongoing edits of an already-published story, consistent with `012-story-editing-and-review`'s existing "editing doesn't change publish status, takes effect immediately" behavior.
- There is no separate approval or sign-off step beyond the administrator's own test play; a single qualifying exchange is sufficient to unblock publish, trusting the administrator's judgment about whether further testing is warranted.
- Per explicit product decision, there is no "assignment" or targeting capability for published stories: once published, a story is available to every player able to reach the adventure list, with no per-player or per-group restriction, consistent with the existing `005-story-publishing` model. The design prototype's "Publish & assign" button label refers only to the publish action; no separate assignment feature exists.
