# Feature Specification: Core Gameplay

**Feature Branch**: `008-core-gameplay`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: merges "Play an Adventure Story" (originally `001-adventure-game` User Story 1, including content safety, rate limiting, and session exclusivity) with "Game Concludes According to Configured Completion Criteria" (originally `003-game-setup-and-authoring` User Story 3) — the narrative play loop and how that loop ends are the same core mechanic.

**Input**: User description (combined): "A player opens the application in a web browser, chooses an available story, and plays through it entirely by typing natural-language actions. After each action, the system responds with narrative text... The game can be configured to complete after a certain duration - for example 30 minutes. The game can be configured to complete when certain criteria have been fulfilled (success criteria). The game can be configured to complete when the player has failed in the game (exit criteria). The game can be configured to complete when any or all of the above criteria is met."

**Design Reference**: [specs/designs/03-play.html](../designs/03-play.html), story pane & status panel (see [specs/designs/README.md](../designs/README.md)). Note: the screen's "Stuck? Get a hint" action is not currently covered by this spec's functional requirements — see the Gaps note in the design README.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player Plays Through an Adventure via Natural Language (Priority: P1)

Once a player has set up a game (see `006-adventure-and-character-setup`), they play entirely by typing natural-language actions ("look around," "open the door," "ask the innkeeper about the map"). After each action, the system responds with narrative text describing what happens next, consistent with everything that has happened so far in that session.

**Why this priority**: This is the core value of the product — the actual game experience. Nothing else matters if this loop doesn't work.

**Independent Test**: With a play session already set up (adventure, character name, character type), submit a sequence of natural-language actions and verify each response is narratively coherent, reflects prior actions, and is delivered through the text interface.

**Acceptance Scenarios**:

1. **Given** a newly set-up play session, **When** it begins, **Then** the system presents an opening narrative passage establishing the scene, consistent with the chosen adventure and character.
2. **Given** an active play session with prior history, **When** the player types a free-text action, **Then** the system returns a narrative response consistent with the story's setting and the session's prior events.
3. **Given** a concluded session (see User Story 2), **When** the player submits another action, **Then** the system indicates the story has ended rather than generating further narrative.
4. **Given** an active play session, **When** a second interaction is attempted against it while one is already in progress, **Then** the system rejects or defers the second interaction so session state is never corrupted or interleaved.

---

### User Story 2 - Game Concludes According to Configured Completion Criteria (Priority: P2)

While a player is in an active game, the game automatically ends when the conditions the administrator configured for that adventure are met: a time limit is reached, a defined success outcome is achieved, a defined failure outcome occurs, or (depending on configuration) a combination of these.

**Why this priority**: Correctly ending a session is as important as starting one — a game that never ends, or ends incorrectly, undermines the whole experience. It builds directly on User Story 1.

**Independent Test**: Configure one adventure with a short time limit and separately configure another with a success condition; play each to the point the configured condition is met and verify the session concludes for that reason and no other.

**Acceptance Scenarios**:

1. **Given** an adventure configured with a maximum duration, **When** a play session reaches that duration, **Then** the system ends the session and narrates the conclusion, even if the player has not reached any other ending.
2. **Given** an adventure configured with success criteria, **When** a player's actions satisfy those criteria, **Then** the system ends the session as a successful outcome.
3. **Given** an adventure configured with failure/exit criteria, **When** a player's actions meet those criteria, **Then** the system ends the session as a failed outcome.
4. **Given** an adventure configured with more than one completion criterion and a rule that any one of them ends the game, **When** the first of those criteria is met, **Then** the session ends immediately without waiting for the others.
5. **Given** an adventure configured with more than one completion criterion and a rule that all of them must be met, **When** only some of the configured criteria have been satisfied, **Then** the session continues until the remaining criteria are also satisfied (or the game is otherwise ended).

---

### Edge Cases

- Player submits input that is nonsensical or unrelated to the story (e.g., gibberish, or a request entirely outside the fiction): the system responds in a way that keeps the player in the narrative (e.g., "that doesn't seem to work here") rather than erroring.
- Player input is flagged by content safety screening: the system does not forward or display the unsafe content, and instead returns a clear, in-context message.
- A player submits requests faster than the allowed rate: the system informs them clearly rather than silently failing or crashing.
- Two completion criteria are both satisfied at effectively the same moment (e.g., the time limit expires on the same action that also meets the success criteria): the system ends the session exactly once, with one clearly attributed reason.
- Multiple players independently start sessions against the same adventure at the same time: each session is exclusive to the player who started it, with no visibility or interference between them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a player to interact with an in-progress adventure exclusively through free-form natural-language text input.
- **FR-002**: System MUST respond to each player input with narrative text that reflects both the adventure's content and the accumulated history of that player's session.
- **FR-003**: System MUST retain the state/context of a player's session across multiple interactions so later responses remain consistent with earlier ones.
- **FR-004**: System MUST screen natural-language input and generated narrative output for unsafe or disallowed content and MUST NOT display unsafe content to a user.
- **FR-005**: System MUST limit how frequently a single player can submit interactions, and MUST communicate clearly to the player when that limit is reached.
- **FR-006**: System MUST ensure each play session is exclusive to the single player who started it — no other user may view or act within that session. Any number of players may hold their own separate, concurrent sessions, including against the same adventure.
- **FR-007**: System MUST support configuring, per adventure, one or more of the following completion conditions: a maximum time duration, one or more success criteria, and one or more failure/exit criteria.
- **FR-008**: System MUST support configuring, per adventure with more than one completion condition, whether the game ends when any one configured condition is met or only when all configured conditions are met.
- **FR-009**: System MUST automatically end a play session as soon as its adventure's configured completion condition(s) are satisfied, and MUST record which condition (or combination) caused the ending.
- **FR-010**: System MUST recognize when a session reaches a defined ending and prevent further gameplay actions within that concluded session.
- **FR-011**: Each distinct type of player interaction and each distinct completion-condition type/combination MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Play Session**: One player's individual playthrough of a specific adventure — tracks the ongoing narrative history and current state, is exclusive to the player who started it, and ends when its configured completion criteria are met.
- **Player Interaction**: A single natural-language input from a player during a Play Session and the narrative response it produces — the atomic unit of gameplay.
- **Completion Criteria**: The set of conditions configured on an adventure (defined during story creation/import — see `004-story-creation-done`, `011-story-import`) that determine when a play session automatically ends — a maximum duration, success condition(s), and/or failure condition(s) — together with a rule for whether any one or all configured conditions must be met.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player receives a narrative response to a submitted action within a few seconds, so play feels like a real-time conversation rather than a batch process.
- **SC-002**: 100% of distinct player-interaction types are covered by an automated test that verifies real expected behavior.
- **SC-003**: In evaluation testing, disallowed or unsafe content submitted by a player is withheld from display to any user in 100% of tested cases.
- **SC-004**: In evaluation testing, concurrent interaction attempts against the same active play session never result in corrupted, interleaved, or lost session state.
- **SC-005**: A player who exceeds the allowed request rate always receives a clear, human-readable notice rather than a silent failure or an unrelated error.
- **SC-006**: 100% of tested play sessions conclude for the specific reason their adventure was configured for (duration, success, failure, or the correct any/all combination), with no session left indefinitely open past its configured condition.

## Assumptions

- This spec assumes a play session has already been set up with a chosen adventure, character name, and character type, per `006-adventure-and-character-setup`; it does not redefine that setup flow.
- Completion criteria (duration, success, failure, and the any/all combination rule) are authored as part of a story's configuration in `004-story-creation-done` or `011-story-import`; this spec only covers how they are enforced during play, not how they are defined.
- Saving progress mid-session and resuming later is a separate capability (see `009-save-and-continue`); this spec covers the moment-to-moment play loop and its natural conclusion, not persistence across visits.
