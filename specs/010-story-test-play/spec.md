# Feature Specification: Story Test Play

**Feature Branch**: `010-story-test-play`

**Created**: 2026-08-28

**Status**: Draft

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), step 05 "Test play" (see [specs/designs/README.md](../designs/README.md)). The prototype's "Flag this reply" button has no requirement behind it — in-session flagging is out of scope (see Assumptions).

**Input**: User description: "create a new spec that matches the test play section in specs/designs/04-admin-wizard.html - reconcile with the rest of the specifications. there should be no 'assignment' requirement - once the story is published then it is available to all."

**Split**: The publish gate is specified in [017-story-publish-test-play-gate](../017-story-publish-test-play-gate/spec.md), which depends on the Test Play Exchange concept defined here.

## Clarifications

### Session 2026-09-08

- Q: Does "a play through" require reaching a story ending, or just an ordinary play session? → A: An ordinary play session with nothing extra; this spec stays silent on what counts as sufficient testing — `017-story-publish-test-play-gate` alone owns that.
- Q: How should the design prototype's now-unspecified "Flag this reply" button be handled? → A: Record it as deliberately not implemented in `specs/designs/README.md`; leave the prototype HTML unchanged.
- Q: Is an explicit restart action retained? → A: Yes, but it aborts rather than resets — after a warning shown before any action, the session is deleted and the administrator returns to the edit story page.
- Q: Do exchanges from a deleted session still count toward the publish gate? → A: Yes. Attempting a playthrough satisfies the gate; completing one is not required.
- Q: What happens when a test play reaches an ending? → A: The administrator is told the playthrough concluded and is offered Publish (confirmed, then to the story list) and Edit (back to the wizard). Visual design is deferred.
- Q: Should publish confirmation apply everywhere or only at test-play conclusion? → A: Everywhere — `005-story-publishing-done` FR-013 is amended so publish and unpublish both require confirmation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Test-Plays a Draft Story Before Publishing (Priority: P1)

An administrator starts an interactive test conversation against a story's current saved configuration — typing test instructions and receiving narrative responses, the same way a real player would — to verify the story behaves as intended before it is ever shown to a player.

**Why this priority**: This is the core value of the feature — catching a broken or unsafe story before real players see it. Nothing else in this feature matters without it.

**Independent Test**: With one draft story that has a saved world prompt, character types, and completion criteria, start a test-play session, submit a few test instructions, and verify narrative responses are generated consistent with that configuration, using the same interaction model as real gameplay.

**Acceptance Scenarios**:

1. **Given** a story with a saved configuration, **When** an administrator starts a test-play session against it, **Then** the system generates narrative responses to the administrator's test instructions using that story's current configuration, the same way it would for a real player.
2. **Given** an active test-play session, **When** the administrator submits a test instruction, **Then** the response is generated and displayed, clearly marked as a test/draft interaction rather than a real player session.
3. **Given** a story configured with completion criteria, **When** the administrator's test actions satisfy one of those criteria during test play, **Then** the session concludes the same way a real play session would, and the administrator is told the playthrough has concluded.
4. **Given** a concluded test-play session, **When** the administrator chooses to publish, **Then** they are asked to confirm, and on confirming the story is published and they are taken to the story list showing that story's updated status.
5. **Given** a concluded test-play session, **When** the administrator chooses to edit, **Then** they are returned to the story wizard with that story loaded.
6. **Given** an active test-play session, **When** the administrator selects restart, **Then** they are warned — before anything happens — that the session will be aborted and deleted and that they will return to the edit story page; on confirming, the session is deleted and they are returned there.

---

### Edge Cases

- Two administrators test-play the same draft story at the same time: each gets their own independent test-play session; either session's exchanges are visible only within that session.
- An administrator dismisses the restart warning: the session continues unaffected, with its conversation intact.
- A draft story has no completion criteria configured yet: test play still allows narrative interaction, but no criteria-based ending can be reached, so restart is the only exit from the session.
- An administrator publishes from the conclusion screen and the publish is blocked or fails: they stay on the conclusion screen and are told why, rather than being taken to the story list.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to start an interactive test-play session against a story's current saved configuration.
- **FR-002**: Test play MUST generate narrative responses to the administrator's test instructions using the same narrative-generation and content-safety-screening behavior as real gameplay (see `008-core-gameplay-done`).
- **FR-003**: A test-play session MUST be visibly distinguished from a real player session, so an administrator never mistakes it for actual gameplay.
- **FR-004**: If the story being tested has completion criteria configured, test play MUST enforce them the same way a real play session would, so the administrator can verify the story's ending behavior.
- **FR-005**: System MUST allow an administrator to restart a test-play session. Selecting restart MUST first warn the administrator that the session will be aborted and deleted and that they will be returned to the edit story page; only on confirmation MUST the session be deleted and the administrator returned there. Dismissing the warning MUST leave the session and its conversation untouched.
- **FR-006**: When a test-play session concludes by satisfying a completion criterion (FR-004), the system MUST tell the administrator the playthrough has concluded and offer both a publish action (FR-007) and an edit action (FR-008).
- **FR-007**: The publish action offered at conclusion MUST ask the administrator to confirm before publishing; on confirmation it MUST publish the story via the same action and preconditions as every other publish entry point (`005-story-publishing-done`, `017-story-publish-test-play-gate`), never a separate publish path, and then take the administrator to the administrator story list showing that story's updated published status.
- **FR-008**: The edit action offered at conclusion MUST return the administrator to the story wizard with that story loaded for further configuration (see `012-story-editing-and-review` FR-003).
- **FR-009**: A test-play session and its exchanges MUST NOT be visible to, or interfere with, any other administrator's test-play session or any real player's play session.
- **FR-010**: Deleting a test-play session (FR-005) MUST NOT reset the story's recorded test-play status; a Test Play Exchange that has occurred against the story's current saved content continues to count for `017-story-publish-test-play-gate`.
- **FR-011**: This feature's test-play screen MAY ship without a visual design pass — no mockup and no bespoke layout are required before it is considered complete, as an approved design is expected later. It MUST still be accessible and semantically marked up (headings, labelled controls, keyboard operability, meaningful link/button text), and MUST NOT introduce off-system colors, fonts, or spacing values.
- **FR-012**: Each distinct test-play outcome (interactive response generation, completion-criteria triggering during test, the restart warning being dismissed, restart being confirmed, publishing from the conclusion screen, and editing from the conclusion screen) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Test Play Session**: An ephemeral, administrator-only play-through of a story's current saved configuration, used to verify its behavior before publishing; distinct from a Play Session (`008-core-gameplay-done`), which is a real player's playthrough.
- **Test Play Exchange**: A single submitted test instruction and the narrative response it produces during a Test Play Session. This is the unit `017-story-publish-test-play-gate` counts; how many are required, if any, is that spec's decision, not this one's.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can verify a draft story's narrative behavior, including its configured ending conditions, entirely through test play, without needing to publish it or use a separate player account.
- **SC-002**: Test-play sessions never affect or appear within any real player's play session or another administrator's test-play session, in testing.
- **SC-003**: From a concluded test play, an administrator reaches either the published story in the story list or the story wizard loaded with that story, in a single action plus a confirmation.

## Assumptions

- Test-play sessions are not persisted as Play Sessions and do not count toward any player-facing history, save/continue behavior (`009-save-and-continue`), or gameplay telemetry that is scoped to real players.
- This spec defines what a Test Play Exchange is; whether and how many are required before a story may be published is specified in `017-story-publish-test-play-gate`.
- There is no in-session flagging, annotation, or note-taking on a test response. Remediation happens after the test by editing the story through the mechanisms already specified — the wizard (`012-story-editing-and-review` FR-003, `004-story-creation-done`) — so this feature adds no editing surface of its own. The design prototype's "Flag this reply" button is therefore deliberately unimplemented, recorded as such in `specs/designs/README.md`.
- FR-007's confirmation depends on an amendment to `005-story-publishing-done` FR-013 (publish now confirms, as unpublish already did). That amendment applies to the wizard and story-list entry points too, both of which already ship without a publish confirmation, so bringing them into line is in-scope implementation work for this feature rather than a change confined to the new screen.
- Deferring this screen's visual design (FR-011) is the kind of deviation constitution Principle VIII expects to be raised as an explicit, justified exception in the implementation plan's Constitution Check — the plan MUST record it there rather than treat the design-system requirement as silently satisfied. The deferral covers appearance only; the accessibility bar applies in full.
