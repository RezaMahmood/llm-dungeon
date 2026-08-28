# Feature Specification: Adventure and Character Setup

**Feature Branch**: `006-adventure-and-character-setup`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: merges "Choose Among Multiple Stories" (originally `001-adventure-game` User Story 3) with the character-setup portion of "Player Sets Up and Starts a New Game" (originally `003-game-setup-and-authoring` User Story 1) — both describe the same pre-play setup flow a player goes through before a new game session begins.

**Input**: User description (combined): "A player browses the set of published stories and picks which one to start. ... Player selects what story they want (this is predefined by the administrator), player selects a character name, player selects a character type (defined by administrator) - they have to be given a choice of character types. Only once these selections have been made can the player start the game itself."

**Design Reference**: [specs/designs/02-story-select.html](../designs/02-story-select.html), "Start something new" section (see [specs/designs/README.md](../designs/README.md))

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player Selects an Adventure and Creates a Character (Priority: P1)

A player choosing to start a new game first picks which published adventure to play from a list, then gives their character a name and picks one of the character types the administrator defined for that adventure. Only after all three choices are made can the player actually enter the game.

**Why this priority**: This is the required setup step between "player wants to start a new game" and "player is playing" (the play loop itself is covered by `008-core-gameplay`). Without it, a player has no way to choose what and who they're playing as.

**Independent Test**: With one published adventure that defines at least two character types, select the adventure, enter a character name, choose a character type, and verify play only begins after all three are supplied — and that the chosen name/type are reflected in the resulting session.

**Acceptance Scenarios**:

1. **Given** a player has chosen "start a new game," **When** they view the list of available adventures, **Then** only published adventures are shown (see `005-story-publishing`), each distinguishable by name.
2. **Given** a player has selected an adventure, **When** they proceed to set up their character, **Then** they are prompted for a character name and shown the set of character types defined for that specific adventure.
3. **Given** a player has selected an adventure but has not yet supplied both a character name and a character type, **When** they attempt to start playing, **Then** the system prevents play from starting and indicates what is still missing.
4. **Given** a player has supplied an adventure, a character name, and a character type, **When** they confirm their choices, **Then** a new play session begins using that adventure, name, and character type.

---

### Edge Cases

- A player enters a character name that is empty or only whitespace: the system rejects it and asks for a valid name rather than starting a game with a blank identity.
- A player attempts to start a new game after selecting an adventure and a character name but not a character type (or any other incomplete combination): the system blocks starting play and identifies exactly what is missing.
- No adventures are currently published: the player sees a clear message that nothing is available yet, rather than an empty or broken list.
- An adventure defines only a single character type: the player is still shown a choice (of one), rather than the type being silently pre-selected without their confirmation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present a player starting a new game with the list of currently published adventures to choose from, each distinguishable by name.
- **FR-002**: System MUST require a player starting a new game to supply a non-blank character name before play can begin.
- **FR-003**: System MUST require a player starting a new game to choose one character type from the set of character types defined by the administrator for the selected adventure, before play can begin.
- **FR-004**: System MUST prevent a player from starting actual gameplay until an adventure, a character name, and a character type have all been supplied.
- **FR-005**: System MUST identify to the player exactly which setup element(s) are still missing when they attempt to start play prematurely.
- **FR-006**: System MUST display a clear message when no adventures are currently published, rather than an empty adventure list.
- **FR-007**: Each distinct setup step (adventure selection, character name entry, character type selection, and the completeness gate) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Character Type**: An administrator-defined option, scoped to a specific adventure, that a player chooses from when setting up a new game against that adventure (defined in `004-story-creation` / `011-story-import`).
- **Play Session Setup**: The adventure, character name, and character type a player has selected for a given play session before gameplay is permitted to begin.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player can go from choosing "start a new game" to being in active play in three steps or fewer (adventure, name, character type) with no additional required input.
- **SC-002**: 100% of attempts to start play with an incomplete setup (missing adventure, name, or character type) are blocked in testing, with the missing item identified to the player.
- **SC-003**: A player can distinguish and choose between multiple published adventures without needing any explanation beyond what's shown in the list.

## Assumptions

- Character types are defined per adventure by the administrator (as part of that adventure's configuration), not as a single global list shared across all adventures.
- This spec covers only setup; the resulting play session itself, including how completion criteria end it, is defined in `008-core-gameplay`.
- The adventure list shown here is exactly the set of published stories as governed by `005-story-publishing`; this spec does not alter or duplicate that publishing logic.
