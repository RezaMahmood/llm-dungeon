# Feature Specification: Story Test Play

**Feature Branch**: `010-story-test-play`

**Created**: 2026-08-28

**Status**: Draft

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), step 05 "Test play" (see [specs/designs/README.md](../designs/README.md))

**Input**: User description: "create a new spec that matches the test play section in specs/designs/04-admin-wizard.html - reconcile with the rest of the specifications. there should be no 'assignment' requirement - once the story is published then it is available to all."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Test-Plays a Draft Story Before Publishing (Priority: P1)

An administrator starts an interactive test conversation against a story's current saved configuration — typing test instructions and receiving narrative responses, the same way a real player would — to verify the story behaves as intended before it is ever shown to a player.

**Why this priority**: This is the core value of the feature — catching a broken or unsafe story before real players see it. Nothing else in this feature matters without it.

**Independent Test**: With one draft story that has a saved world prompt, character types, and completion criteria, start a test-play session, submit a few test instructions, and verify narrative responses are generated consistent with that configuration, using the same interaction model as real gameplay.

**Acceptance Scenarios**:

1. **Given** a story with a saved configuration, **When** an administrator starts a test-play session against it, **Then** the system generates narrative responses to the administrator's test instructions using that story's current configuration, the same way it would for a real player.
2. **Given** an active test-play session, **When** the administrator submits a test instruction, **Then** the response is generated and displayed, clearly marked as a test/draft interaction rather than a real player session.
3. **Given** a story configured with completion criteria, **When** the administrator's test actions satisfy one of those criteria during test play, **Then** the test-play session concludes the same way a real play session would, so the administrator can verify the ending behaves correctly.
4. **Given** an active test-play session, **When** the administrator restarts the test, **Then** the test conversation resets to the beginning, discarding prior test history, using the story's current configuration.

---

### User Story 2 - Administrator Flags a Problematic Test Response (Priority: P2)

While test-playing, the administrator can flag any single narrative response as a problem, so they can find it again when refining the story.

**Why this priority**: This captures the actual value of testing — noticing something wrong — but it's a smaller capability layered on top of test play itself (User Story 1).

**Independent Test**: During a test-play session, flag one response and verify it is visibly marked/distinguishable within that session so the administrator can identify it again.

**Acceptance Scenarios**:

1. **Given** an active test-play session with at least one narrative response, **When** the administrator flags that response, **Then** it is marked so the administrator can identify it later within the same test session.
2. **Given** a test-play session is restarted, **When** the restart completes, **Then** any previously flagged responses from the discarded conversation are cleared along with the rest of that conversation's history.

---

### User Story 3 - A Story Cannot Be Published Without a Completed Test Play (Priority: P3)

The publish action (see `005-story-publishing`) is blocked until the story has had at least one test-play exchange since its content was last changed.

**Why this priority**: This is what makes test play meaningful rather than optional busywork. It depends on both User Story 1 (test play exists) and `005-story-publishing` (a publish action exists to gate).

**Independent Test**: Attempt to publish a brand-new draft story that has never been test-played and verify it is blocked; perform one test-play exchange, then verify publish succeeds; edit the story's content again and verify publish is blocked again until another test-play exchange occurs.

**Acceptance Scenarios**:

1. **Given** a draft story that has never been test-played, **When** an administrator attempts to publish it, **Then** the system blocks the publish action and indicates a test play is required first.
2. **Given** a draft story that has had at least one test-play exchange since its content was last saved, **When** an administrator attempts to publish it, **Then** the publish action is allowed to proceed.
3. **Given** a story that previously had a qualifying test play, **When** its content (e.g., world prompt, character types, completion criteria) is changed and saved again, **Then** the test-play requirement is reset, and publishing is blocked again until a new test-play exchange occurs against the updated content.
4. **Given** a story that is already published, **When** an administrator edits its content, **Then** the edit takes effect immediately without requiring a new test play, consistent with existing story-editing behavior (see `012-story-editing-and-review`); the test-play gate applies only to the publish action itself, not to edits of an already-published story.

---

### Edge Cases

- An administrator starts a test-play session, takes no actions, and leaves: no test-play exchange has occurred, so the publish gate remains unsatisfied.
- Two administrators test-play the same draft story at the same time: each gets their own independent test-play session; either one completing a qualifying exchange satisfies the publish gate for that story.
- An administrator flags a response and then continues the same test conversation: the flag doesn't interrupt or alter the ongoing test conversation.
- A draft story has no completion criteria configured yet: test play still allows narrative interaction, but there is no criteria-based ending to verify during the test.
- An administrator publishes a story, then edits its content while players are mid-session: this spec does not change that existing behavior (see `012-story-editing-and-review`) — the test-play gate does not apply, since the story is already published.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to start an interactive test-play session against a story's current saved configuration.
- **FR-002**: Test play MUST generate narrative responses to the administrator's test instructions using the same narrative-generation and content-safety-screening behavior as real gameplay (see `008-core-gameplay`).
- **FR-003**: A test-play session MUST be visibly distinguished from a real player session, so an administrator never mistakes it for actual gameplay.
- **FR-004**: If the story being tested has completion criteria configured, test play MUST enforce them the same way a real play session would, so the administrator can verify the story's ending behavior.
- **FR-005**: System MUST allow an administrator to restart a test-play session, discarding its current conversation and starting a fresh one against the story's current configuration.
- **FR-006**: System MUST allow an administrator to flag any individual narrative response received during a test-play session, and MUST make flagged responses identifiable within that session.
- **FR-007**: A test-play session and anything flagged within it MUST NOT be visible to, or interfere with, any other administrator's test-play session or any real player's play session.
- **FR-008**: System MUST track, per story, whether at least one test-play exchange (a submitted test instruction and its resulting response) has occurred since that story's content was last saved.
- **FR-009**: The publish action defined in `005-story-publishing` MUST be blocked, with a clear explanation, unless the story has at least one test-play exchange recorded since its content was last saved.
- **FR-010**: Saving a change to a story's content MUST reset its recorded test-play status, so a previously satisfied publish gate does not carry over to changed content.
- **FR-011**: The test-play gate applies only to the publish action; it MUST NOT block or otherwise affect edits to a story that is already published (see `012-story-editing-and-review`).
- **FR-012**: Publishing a story MUST NOT include, or depend on, any capability to target or restrict it to specific players or groups — once published, a story is available to every player able to reach the adventure list, with no assignment step (see `005-story-publishing`).
- **FR-013**: Each distinct test-play outcome (interactive response generation, completion-criteria triggering during test, restart, flagging a response, publish blocked with no test play, publish allowed after a qualifying test play, publish blocked again after a content change) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Test Play Session**: An ephemeral, administrator-only play-through of a story's current saved configuration, used to verify its behavior before publishing; distinct from a Play Session (`008-core-gameplay`), which is a real player's playthrough.
- **Test Play Exchange**: A single submitted test instruction and the narrative response it produces during a Test Play Session — the unit that satisfies the publish gate.
- **Flagged Response**: A Test Play Exchange's response that an administrator has marked as a problem to revisit, identifiable within its Test Play Session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can verify a draft story's narrative behavior, including its configured ending conditions, entirely through test play, without needing to publish it or use a separate player account.
- **SC-002**: 100% of publish attempts against a story with no qualifying test-play exchange since its last content change are blocked in testing.
- **SC-003**: 100% of publish attempts against a story with a qualifying test-play exchange since its last content change succeed (assuming no other publish requirement is violated) in testing.
- **SC-004**: 100% of content changes to a story in testing reset its test-play status, requiring a new qualifying exchange before the next publish attempt.
- **SC-005**: Test-play sessions never affect or appear within any real player's play session or another administrator's test-play session, in testing.

## Assumptions

- "Completed a test play" means at least one test-play exchange (a submitted instruction and its response) has occurred against the story's current saved content — not necessarily a full playthrough to one of the story's own ending conditions. This is testing/QA in spirit, not a requirement to fully complete the adventure.
- The test-play gate applies only to the transition from unpublished to published (the publish action itself, per `005-story-publishing`); it does not apply to ongoing edits of an already-published story, consistent with `012-story-editing-and-review`'s existing "editing doesn't change publish status, takes effect immediately" behavior.
- Test-play sessions are not persisted as Play Sessions and do not count toward any player-facing history, save/continue behavior (`009-save-and-continue`), or gameplay telemetry that is scoped to real players.
- There is no separate approval or sign-off step beyond the administrator's own test play; a single qualifying exchange is sufficient to unblock publish, trusting the administrator's judgment about whether further testing is warranted.
- Per explicit product decision, there is no "assignment" or targeting capability for published stories: once published, a story is available to every player able to reach the adventure list, with no per-player or per-group restriction, consistent with the existing `005-story-publishing` model. The design prototype's "Publish & assign" button label refers only to the publish action; no separate assignment feature exists.
