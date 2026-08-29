# Feature Specification: Story Test Play

**Feature Branch**: `010-story-test-play`

**Created**: 2026-08-28

**Status**: Draft

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), step 05 "Test play" (see [specs/designs/README.md](../designs/README.md))

**Input**: User description: "create a new spec that matches the test play section in specs/designs/04-admin-wizard.html - reconcile with the rest of the specifications. there should be no 'assignment' requirement - once the story is published then it is available to all."

**Split**: 2026-08-29 — this spec originally also contained a third user story, "A Story Cannot Be Published Without a Completed Test Play", which made publishing itself conditional on this feature. It has been split out into [017-story-publish-test-play-gate](../017-story-publish-test-play-gate/spec.md) so this spec covers at most two user stories (running a test-play session, and flagging a response within one). The publish gate depends on the Test Play Exchange concept this spec defines.

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

### Edge Cases

- Two administrators test-play the same draft story at the same time: each gets their own independent test-play session; either session's exchanges are visible only within that session.
- An administrator flags a response and then continues the same test conversation: the flag doesn't interrupt or alter the ongoing test conversation.
- A draft story has no completion criteria configured yet: test play still allows narrative interaction, but there is no criteria-based ending to verify during the test.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to start an interactive test-play session against a story's current saved configuration.
- **FR-002**: Test play MUST generate narrative responses to the administrator's test instructions using the same narrative-generation and content-safety-screening behavior as real gameplay (see `008-core-gameplay`).
- **FR-003**: A test-play session MUST be visibly distinguished from a real player session, so an administrator never mistakes it for actual gameplay.
- **FR-004**: If the story being tested has completion criteria configured, test play MUST enforce them the same way a real play session would, so the administrator can verify the story's ending behavior.
- **FR-005**: System MUST allow an administrator to restart a test-play session, discarding its current conversation and starting a fresh one against the story's current configuration.
- **FR-006**: System MUST allow an administrator to flag any individual narrative response received during a test-play session, and MUST make flagged responses identifiable within that session.
- **FR-007**: A test-play session and anything flagged within it MUST NOT be visible to, or interfere with, any other administrator's test-play session or any real player's play session.
- **FR-008**: Each distinct test-play outcome (interactive response generation, completion-criteria triggering during test, restart, flagging a response) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Test Play Session**: An ephemeral, administrator-only play-through of a story's current saved configuration, used to verify its behavior before publishing; distinct from a Play Session (`008-core-gameplay`), which is a real player's playthrough.
- **Test Play Exchange**: A single submitted test instruction and the narrative response it produces during a Test Play Session. This is the unit `017-story-publish-test-play-gate` uses to determine whether a story's publish gate is satisfied.
- **Flagged Response**: A Test Play Exchange's response that an administrator has marked as a problem to revisit, identifiable within its Test Play Session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can verify a draft story's narrative behavior, including its configured ending conditions, entirely through test play, without needing to publish it or use a separate player account.
- **SC-002**: Test-play sessions never affect or appear within any real player's play session or another administrator's test-play session, in testing.

## Assumptions

- Test-play sessions are not persisted as Play Sessions and do not count toward any player-facing history, save/continue behavior (`009-save-and-continue`), or gameplay telemetry that is scoped to real players.
- What counts as a Test Play Exchange (a submitted instruction and its response) is defined here; whether and how many such exchanges are required before a story may be published is a separate concern, specified in `017-story-publish-test-play-gate`.
