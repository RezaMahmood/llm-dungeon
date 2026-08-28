# Feature Specification: Save and Continue

**Feature Branch**: `009-save-and-continue`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: merges "Player Continues a Saved Game" and "Player Saves Progress and Returns Home" — originally User Stories 2 and 4 within `003-game-setup-and-authoring` — into a single persistence-focused domain, split out from core gameplay (`008-core-gameplay`) since saving/resuming across visits is a distinct concern from the moment-to-moment play loop.

**Input**: User description (combined): "Continue Game: Select games associated to profile; Play Game; End/Save Game; Return to Home Page. Save Game: Game state is saved; Return to Home page. Logout: Ask player to save game (if they are currently in a game)."

**Design Reference**: [specs/designs/02-story-select.html](../designs/02-story-select.html), "stories in progress" / Resume section, and [specs/designs/03-play.html](../designs/03-play.html), checkpoint-save/pause-and-exit controls (see [specs/designs/README.md](../designs/README.md))

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player Continues a Saved Game (Priority: P1)

A returning player chooses "continue game," sees the games associated with their own profile, and resumes one from where they left off.

**Why this priority**: Long-form play across multiple visits depends on this; it is the primary reason persistence exists at all.

**Independent Test**: With a player who has one previously saved, in-progress game, select "continue game," verify only that player's own saved games are listed, and verify resuming one restores the prior narrative state.

**Acceptance Scenarios**:

1. **Given** a player has one or more saved, in-progress games, **When** they choose "continue game," **Then** they see a list of only their own saved games, not any other player's.
2. **Given** a player selects one of their saved games, **When** the game resumes, **Then** play continues from the saved state, consistent with everything that happened before it was saved.
3. **Given** a player has no saved, in-progress games, **When** they choose "continue game," **Then** they see a clear indication that there is nothing to continue, rather than an empty or broken screen.

---

### User Story 2 - Player Saves Progress and Returns Home (Priority: P2)

At any point during an active game, a player can explicitly save their current progress and return to the home screen, and the system also offers to save when the player tries to log out while a game is in progress.

**Why this priority**: This protects player progress between sessions and prevents accidental loss on logout; it's a safety-net capability layered on top of an already-working play loop and login flow.

**Independent Test**: Start a game, take a few actions, explicitly save and return home, then verify (via User Story 1's continue flow) that the saved state matches what was in progress at the time of saving.

**Acceptance Scenarios**:

1. **Given** a player is in an active, unconcluded game, **When** they choose to save and return home, **Then** the current game state is persisted and the player is returned to the home screen.
2. **Given** a player is in an active, unconcluded game, **When** they attempt to log out, **Then** the system asks whether they want to save their progress before logging out.
3. **Given** a player is prompted to save on logout and chooses to save, **When** they next log in and continue that game, **Then** their progress from just before logout is present.
4. **Given** a player is prompted to save on logout and declines, **When** they next log in and continue that game, **Then** their progress reflects the last point it was explicitly or automatically saved, not the declined save.
5. **Given** a player is not currently in an active game, **When** they log out, **Then** they are not prompted to save.

---

### Edge Cases

- A player's game already ended (via a completion criterion — see `008-core-gameplay`) before they log out: they are not prompted to save, since a concluded game has nothing further to save.
- A player explicitly saves the same game twice in a row without taking any action in between: the second save succeeds and results in an equivalent saved state (a no-op save).
- A player has multiple saved, in-progress games across different adventures: the continue-game list distinguishes them clearly enough for the player to pick the right one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a player to view and resume any of their own previously saved, in-progress games, and MUST NOT show a player another player's saved games.
- **FR-002**: System MUST display a clear message when a player has no saved, in-progress games to continue.
- **FR-003**: System MUST allow a player to explicitly save their current game progress and return to the home screen without ending the game.
- **FR-004**: System MUST prompt a player to save their progress when they attempt to log out while a game is currently in progress, and MUST NOT prompt them when no game is in progress or the game has already concluded.
- **FR-005**: System MUST persist a player's progress from just before logout when they accept the save prompt.
- **FR-006**: Resuming a saved game MUST restore play in a state consistent with everything that happened before it was saved.
- **FR-007**: Each distinct persistence outcome (continue with saved games present, continue with none present, explicit save, logout-with-save-accepted, logout-with-save-declined, logout with no active game) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Saved Game**: The persisted state of a player's in-progress Play Session (see `008-core-gameplay`), associated with the player identity that owns it, resumable via the continue-game flow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player who explicitly saves and returns home, or who saves via the logout prompt, can later resume their game with progress matching exactly what existed at the point of saving.
- **SC-002**: 100% of continue-game lists in testing show only the requesting player's own saved games.
- **SC-003**: 100% of logout attempts while a game is in progress in testing trigger the save prompt; 100% of logout attempts with no active game do not.

## Assumptions

- "Games associated to profile" (continue-game listing) refers to play sessions started by the same authenticated player identity (see `002-login-and-access-control`); no sharing or transfer of saved games between identities is in scope.
- Declining the save prompt on logout does not delete or roll back the game; it simply logs the player out without capturing progress made since the last save.
- There is no defined limit on the number of in-progress saved games a single player may have across different adventures.
