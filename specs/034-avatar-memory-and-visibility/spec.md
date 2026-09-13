# Feature Specification: Remembering and Showing a Player's Avatar

**Feature Branch**: `034-avatar-memory-and-visibility`

**Created**: 2026-09-13

**Status**: Draft

**Part of**: [#336](https://github.com/RezaMahmood/llm-dungeon/issues/336) — the third of three slices. See *Relationship to the other slices*.

**Input**: Split out of `032-story-archetypes-player-avatar` during spec review, as two small additions that both depend on the avatar existing but not on each other.

## Overview

Once a player writes an avatar description at setup (`032-story-archetypes-player-avatar`), two things are missing:

- **They cannot see it again.** The description is written once and never shown, so a player part-way through a long session has no way to check who they said they were.
- **They must retype it every time.** A player returning to an adventure they have played before starts from an empty field, though they have already written a description that suited it.

This slice adds both: the description is shown read-only during play, and it is remembered per adventure and offered back as a starting point next time. Neither changes how a session is narrated.

## Relationship to the other slices

Depends on `032-story-archetypes-player-avatar`, which creates the avatar description this slice stores and displays. It **must merge after it**. It is unrelated to `033-story-cast-in-narration`.

The two halves of this slice — remembering and showing — are independent of each other and may be implemented and tested in either order.

## Clarifications

### Session 2026-09-13

- Q: During play, where should the player be able to see the avatar description they wrote at setup? → A: In the play surface's status panel, read-only, alongside location, goal and progress. The constitution's play-surface screen contract is amended accordingly.
- Q: When a player starts another new game later, should their previous avatar description be offered back as a prefill? → A: Yes. Store it against the player's profile, one valid description per story, prefilled at session start and optional to keep. When a story is deleted, any stored descriptions for that story are deleted with it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Player Can See Who They Are (Priority: P1)

A player part-way through a session can look at the status panel and read the description they wrote, without leaving the play surface.

**Why this priority**: The description is fixed for the life of a session and may run to 500 characters. A player who cannot recall what they committed to has no way to find out.

**Independent Test**: Start a session with a distinctive description, play a few turns, and verify the description is readable in the status panel and that location, goal, and progress remain reachable alongside it.

**Acceptance Scenarios**:

1. **Given** a session started from a player-authored avatar description, **When** the player looks at the status panel during play, **Then** their description is shown there read-only, alongside location, goal, and progress.
2. **Given** the longest permitted description, **When** the status panel is viewed at a 320 px viewport width, **Then** location, goal, and progress all remain reachable and the description does not push them out of view.
3. **Given** a session created before the avatar existed and therefore carrying no description, **When** the status panel is rendered, **Then** it renders without an empty or broken avatar area.

---

### User Story 2 - A Returning Player Does Not Retype (Priority: P2)

A player starting a new game of an adventure they have played before finds the description they last used for it already in the field, and can keep it, edit it, or replace it.

**Why this priority**: Real convenience, and the 20-character minimum makes retyping a genuine cost — but a player who retypes still gets a working game, so this is not what makes the avatar usable.

**Independent Test**: Play an adventure, exit, start a new game of the same adventure, and verify the previous description is prefilled and fully editable.

**Acceptance Scenarios**:

1. **Given** a player has previously started a session for an adventure, **When** they set up a new game for that same adventure, **Then** the description they last used for it is already in the field.
2. **Given** a prefilled description, **When** the player edits or replaces it before starting, **Then** the version they started with is what the session uses and what is stored for next time.
3. **Given** a prefilled description, **When** the player starts with it unchanged, **Then** it is validated exactly as a freshly typed one would be, and the session begins only if it passes.
4. **Given** a player sets up a game for an adventure they have never played, **When** they reach the description field, **Then** it starts empty.
5. **Given** a player has stored descriptions for several adventures, **When** they select a different adventure during setup, **Then** the field shows the stored description for the newly selected adventure.
6. **Given** an administrator deletes an adventure, **When** the deletion completes, **Then** every stored description belonging to it is deleted with it.
7. **Given** an administrator deletes one of a player's sessions, **When** the deletion completes, **Then** that player's stored description for the adventure is untouched and still prefills their next game.

---

### Edge Cases

- A stored description no longer passes validation because the rules tightened since it was written: it is prefilled, then rejected on submission like any other non-conforming description, with the player asked to change it.
- A player abandons setup after editing a prefilled description: nothing is stored, because a description is stored when a session is started, not while it is being typed.
- A player is prefilled from an adventure they played long ago whose content has since been edited: the description is offered as-is; this slice does not judge whether it still suits the adventure.
- A 500-character description is shown in the status panel on the narrowest supported viewport: the panel stays usable and the three authored values stay reachable.
- A session created before the avatar existed is resumed: the status panel renders cleanly with no avatar area, and the player is not prompted to supply one.

## Requirements *(mandatory)*

### Functional Requirements

**Showing the avatar during play**

- **FR-001**: System MUST show the player their own avatar description during play, read-only, in the play surface's status panel alongside location, goal, and progress.
- **FR-002**: The description MUST remain legible and MUST NOT crowd out location, goal, or progress at the 320 px viewport floor the constitution requires.
- **FR-003**: A session with no avatar description — one created before `032-story-archetypes-player-avatar` shipped — MUST render the status panel without an empty or broken avatar area.
- **FR-004**: The constitution's **Play surface** screen contract MUST be amended to name the avatar description among what the status panel shows, so the contract and the shipped surface do not disagree. This amendment MUST be carried by this slice rather than left for later.

**Remembering the avatar per adventure**

- **FR-005**: System MUST store a player's avatar description against their own profile, scoped to the adventure it was written for: at most one stored description per player per adventure, replaced whenever that player starts a new session for that adventure with a different description.
- **FR-006**: System MUST prefill the avatar description field with the player's stored description for the adventure they have selected, when one exists. The prefill is a starting point, not a commitment: the player MUST be able to edit or replace it before starting, and MUST be able to start with it unchanged.
- **FR-007**: System MUST show an empty description field for an adventure the player has no stored description for, and MUST follow the selected adventure when the player changes their selection during setup.
- **FR-008**: System MUST validate a prefilled description on submission exactly as it validates a freshly typed one (`032` FR-003 and its sub-requirements). A stored description MUST NOT bypass validation on the strength of having passed it before.
- **FR-009**: System MUST delete every stored avatar description for an adventure when that adventure is deleted, leaving no stored description belonging to a story that no longer exists.
- **FR-009a**: Deleting a stored avatar description — whether with its adventure (FR-009) or otherwise — MUST NOT decrement any story's cumulative token total. Validation spend recorded under `032` already happened and stays counted.
- **FR-010**: Deleting a play session MUST NOT delete the player's stored avatar description for that adventure, and MUST NOT alter it — the stored description belongs to the player's profile, not to any one session.
- **FR-011**: A player's stored avatar descriptions MUST be visible to and usable by that player alone; one player's stored description MUST NOT be offered to, or disclosed to, another player or an administrator.
- **FR-012**: A stored description MUST be written when a session is started, not while it is being typed, so an abandoned setup leaves nothing stored.

**Testing**

- **FR-013**: Each behaviour this slice introduces MUST have an automated test: the description appearing read-only in the status panel; the panel staying usable at 320 px with the longest permitted description; a description-less session rendering cleanly; storing, prefilling, editing, replacing, and revalidating a stored description; the field following the selected adventure; deletion with the adventure; survival of a session deletion; and one player's stored description being unreachable by another.

### Key Entities

- **Stored Avatar Description**: The most recent avatar description a player used for a given adventure, held against that player's own profile — at most one per player per adventure. Prefills that player's next setup for that adventure; private to them; deleted when the adventure is deleted, and untouched when one of their sessions is deleted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player mid-session can find the description they wrote without leaving the play surface, and location, goal, and progress remain reachable at a 320 px viewport width with the longest permitted description shown.
- **SC-002**: A returning player can start a repeat game of an adventure they have played before without retyping their character description, in the same number of steps as any other setup.
- **SC-003**: Zero stored avatar descriptions survive the deletion of the adventure they belong to, and 100% survive the deletion of a session belonging to that adventure.
- **SC-004**: Zero stored descriptions are readable by anyone other than the player who wrote them, across every access path exercised in testing.
- **SC-005**: 100% of sessions created before the avatar existed render the status panel without error.

## Assumptions

- **Removing a player's account removes their stored avatar descriptions**, by the same reasoning that deletes them with a deleted adventure (FR-009). Stated as an assumption rather than a requirement because account removal is `003-account-provisioning-done`'s territory; confirm it at planning.
- **A stored description is not re-validated at storage time**, only at submission (FR-008). It was validated when the session that stored it began.
- **The status panel's existing contents keep precedence.** Where space is tight, location, goal, and progress win; the description yields.

## Dependencies

- `032-story-archetypes-player-avatar` — creates the avatar description this slice stores and displays. Must merge first.
- `008-core-gameplay-done` / the constitution's **Play surface** screen contract — own the status panel FR-001 adds to, and the contract FR-004 amends. The amendment makes this slice a governance change.
- `025-story-delete-done` — owns story deletion, which FR-009 extends.
- `026-token-usage` / `031-sessions-admin-design-spec` — own session deletion, which FR-010 must leave stored descriptions alone.
- `003-account-provisioning-done` — owns account removal, which the stored-description deletion assumption depends on.

## Out of Scope

- Letting a player edit their avatar description after play has begun; the status panel shows it read-only.
- A library of saved characters a player picks between; exactly one description is stored per player per adventure, replaced rather than accumulated.
- Any administrator-facing view of players' stored avatar descriptions.
- Back-filling a description onto sessions created before the avatar existed.
- Visual redesign of the status panel beyond adding the description to it.
