# Feature Specification: The Story's Cast Reaches the Narration

**Feature Branch**: `033-story-cast-in-narration`

**Created**: 2026-09-13

**Status**: Draft

**Part of**: [#336](https://github.com/RezaMahmood/llm-dungeon/issues/336) — the first of three slices. See *Relationship to the other slices*.

**Input**: Split out of `032-story-archetypes-player-avatar` during spec review, as the one part of that work that is purely additive and can ship on its own.

## Overview

An adventure's authored character roster — the ferryman, the rival houses, the guild that runs the docks — currently reaches the narration only as a label on the player (`Character: {name} ({type})`). The story world it was written to populate never sees it.

This slice makes the roster available to the narration as the story world's **cast**: the characters the player can meet. It changes nothing about how a player sets up a game, and removes nothing. While this ships, a player still picks a roster entry as their identity exactly as they do today; the roster simply starts doing a second job as well.

## Relationship to the other slices

`032-story-archetypes-player-avatar` replaces the player's character-type choice with a player-authored avatar description. This slice **should merge before it**. The reason is ordering, not dependency: `032` stops the roster being the player's identity, so if the roster were not already feeding the narration as cast, there would be an interval in which an authored roster fed nothing at all — worse than today. Shipping this first closes that gap before it opens.

`034-avatar-memory-and-visibility` depends on `032` and is unrelated to this slice.

## Clarifications

### Session 2026-09-13

- Q: When the narration introduces a character, must it come from the authored archetype roster, or may it invent others? → A: Prefer the roster. A named or story-significant character comes from the roster whenever an entry fits; incidental background figures may still be invented.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The Story's Cast Reaches the Narration (Priority: P1)

An administrator's authored roster is given to the narration as the cast the story world contains, so the characters a player meets are drawn from what the administrator wrote rather than invented freely.

**Why this priority**: This is the whole slice. It is what gives the roster a purpose beyond labelling the player.

**Independent Test**: Author an adventure with several distinct roster entries, play several turns, and verify that named characters the player meets are roster entries where one fits rather than newly invented ones.

**Acceptance Scenarios**:

1. **Given** an adventure whose roster names several characters, **When** a turn is narrated, **Then** the roster is available to the narration as the story world's cast, labelled distinctly as such and distinctly separate from the player's own character.
2. **Given** an adventure whose roster names several characters, **When** the narration introduces a named or story-significant character and a roster entry fits the moment, **Then** that roster entry is used rather than a newly invented character.
3. **Given** an adventure whose roster has no entry suited to a moment, **When** the narration needs an incidental background figure there, **Then** it may introduce one without contradicting the roster.
4. **Given** a roster entry carries a description as well as a name, **When** the roster reaches the narration, **Then** the description travels with the name rather than being dropped.
5. **Given** an adventure authored before this change, **When** it is played, **Then** its roster is used as cast with no administrator rework and no change to the story configuration file.

---

### Edge Cases

- An adventure's roster has a single entry and the story calls for a crowd: incidental figures are invented around that entry rather than the narration being stuck with one character.
- A roster entry has a name but no description: the name alone reaches the narration, which is enough for it to be used as cast.
- A roster authored under the old intent reads like a list of player classes ("Warrior", "Scout"): still valid, still supplied as cast. No adventure is invalidated by this change.
- The player's own chosen character type is also a roster entry (as it must be, until `032` ships): the narration receives it once as the player's label and once as part of the cast, and must not treat the player as two characters.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST supply an adventure's authored character roster to the narration as the story world's available cast, labelled distinctly from the player's own character, including each entry's description where one was authored.
- **FR-002**: System MUST direct the narration to draw a named or story-significant character from the roster whenever an entry fits the moment, in preference to inventing one. Incidental background figures, and moments no roster entry fits, remain open to invention — the roster is a precedence rule, not a closed cast list.
- **FR-003**: System MUST continue to require at least one roster entry on a story, and MUST keep the existing publication precondition that depends on it (`005-story-publishing-done`), so no published adventure reaches play without a cast. The justification changes — the story needs a cast, rather than the player needing options — but the rule does not.
- **FR-004**: System MUST accept every existing authored roster unchanged, requiring no administrator rework and no change to the story configuration file's shape for a story to remain valid and playable.
- **FR-005**: System MUST NOT change the player's setup flow, the player's identity, or the administrator's authoring surfaces in this slice. The roster continues to be offered to the player as a choice until `032-story-archetypes-player-avatar` removes it.
- **FR-006**: Each behaviour this slice introduces MUST have an automated test: the roster reaching the narration as distinctly labelled cast, the description travelling with the name, the precedence of roster entries over invented named characters, and an adventure authored before this change playing unchanged.

### Key Entities

- **Character Archetype**: An administrator-authored character belonging to a story's world — a name and an optional description — now supplied to the narration as available cast. Scoped to one adventure. (This is the entity `004-story-creation-done` calls *Character Type*; this slice adds a use for it and changes neither its shape nor its existing use.)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every narrated turn, the material given to the narration contains the story's roster as world cast, labelled distinctly from the player's own character — verifiable in 100% of sampled turns.
- **SC-002**: Across a sampled play-through of an adventure whose roster covers its situations, the named characters the player meets are roster entries, with an invented named character appearing only where no roster entry fits.
- **SC-003**: 100% of adventures authored before this change remain valid and playable with no administrator edit.
- **SC-004**: No change is observable in the player's setup flow: the steps, inputs, and gating are identical before and after this slice.

## Assumptions

- **The roster's stored shape does not change.** A name and an optional description is already what story-world cast needs.
- **The publication precondition holds** for a new reason, as FR-003 states.
- **Narration quality is judged by sampling, not by a deterministic rule.** SC-002 is assessed over a play-through rather than asserted turn-by-turn, because whether an entry "fits a moment" is a narrative judgement.

## Dependencies

- `004-story-creation-done` / `011-story-import` / `012-story-editing-and-review` — own the roster's authoring, import, and review surfaces, which this slice reads but does not change.
- `005-story-publishing-done` — owns the publication precondition FR-003 preserves.
- `008-core-gameplay-done` — owns the per-turn material FR-001 adds to.

## Out of Scope

- Anything about the player's own identity — that is `032-story-archetypes-player-avatar`.
- Administrator-facing wording about what the roster is for; while a player still selects an entry, describing it as story-world cast alone would be inaccurate. It moves with the picker, in `032`.
- Any change to the stored shape of the roster, or a second roster field alongside it.
- Letting a player choose or be assigned a specific roster entry as an ally, companion, or starting relationship.
- Any change to how the narration decides *when* a character appears; this slice sets which characters it should reach for first, not the pacing or staging of their appearances.
