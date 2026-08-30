# Feature Specification: Story Creation

**Feature Branch**: `004-story-creation`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: merges the conversational story-creation capability originally described in `001-adventure-game` (User Story 2) with the guided-wizard framing originally described in `003-game-setup-and-authoring` (User Story 5) — both described the same underlying capability (administrator answers guiding questions, LLM produces a persisted story) at different levels of detail.

**Input**: User description (combined): "An administrator opens the application, starts a new story-creation conversation, and describes their idea in plain language. The system asks guiding questions (setting, characters, plot, win/lose conditions) to draw out a complete story, then persists the resulting story. ... In-App Wizard approach: Answer a set of questions that every story should have; LLM generates a story config file; story config files are automatically persisted."

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), steps 01–04 (name & cover, world & setting, tone & reading level, session length) (see [specs/designs/README.md](../designs/README.md)). These four steps, reachable in any order, are the UI structure for this feature; see Clarifications for how they relate to the guiding-question conversation and where character types and completion criteria are captured.

## Clarifications

### Session 2026-08-29

- Q: Should story creation be built as the four-step wizard shown in the design reference (name & cover, world & setting, tone & reading level, session length — reachable in any order), with the administrator's plain-language description and the system's guiding questions used to fill in each step's fields, or should it be a fully open-ended conversation where the wizard screen doesn't dictate structure at all? → A: Wizard frame + conversational fill-in — the four named steps are the UI structure, reachable in any order; the administrator's plain-language description and the system's guiding-question conversation fill in each step's fields.
- Q: The four wizard steps assigned to this spec (name & cover, world & setting, tone & reading level, session length) have no visible field for character types or completion criteria, both of which FR-002 and SC-003 require to be elicited and persisted — how should these be captured? → A: The wizard needs new, dedicated fields for character types and completion criteria (added to the existing steps or a new step), beyond what the current design mockup shows.
- Q: `008-core-gameplay` already defines "Completion Criteria" as a maximum duration, success condition(s), failure condition(s), and an any/all combination rule, and states this shape is authored in `004-story-creation` — should the new completion-criteria field (FR-008) require that same structured shape? → A: Yes — match `008-core-gameplay`'s structured shape (optional max duration, one or more success conditions, optional failure conditions, and an any/all rule when more than one condition is defined).
- Q: `specs/designs/README.md` flags tone, reading level, session-length target, and chapter count (collected by this spec's wizard steps) as story metadata not yet named as Key Entity attributes anywhere — should this spec add them as explicit Story attributes now? → A: No — left undocumented for a later spec/pass; not resolved by this clarification session.
- Q: Can one administrator have more than one story-creation wizard in progress at the same time, or does starting a new session require finishing/discarding any other in-progress one first? → A: Multiple concurrent drafts allowed — an administrator may have any number of in-progress creation sessions open at once; starting a new one never affects others.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Creates a New Story Through Guided Conversation (Priority: P1)

An administrator starts a new story-creation session inside the administrator wizard (name & cover, world & setting, tone & reading level, session length — reachable in any order) and describes their idea in plain language. Within that wizard, the system asks a structured set of guiding questions — covering, at minimum, setting/plot, character types, and completion criteria, each with dedicated fields for the administrator to define them — to draw out a complete story. Once enough detail has been supplied, the system uses an LLM to generate a complete story configuration and persists it automatically, without a separate manual save step.

**Why this priority**: Without this, the catalog of playable stories cannot grow. It is the entire content pipeline for the product — nothing else in story authoring matters if new stories can't be created.

**Independent Test**: As an administrator, start a creation session from an empty state, answer the guiding questions, and verify a complete story configuration is persisted automatically at the end — with no manual file editing or separate save action required.

**Acceptance Scenarios**:

1. **Given** an administrator starts a new story-creation session, **When** they describe an initial idea, **Then** the system asks guiding questions to elicit the missing elements of a complete story (setting, character types, plot, and completion criteria).
2. **Given** an in-progress creation session, **When** the administrator has supplied enough detail to form a complete story (including at least one character type and at least one completion criterion), **Then** the system generates the story configuration via the LLM and persists it automatically.
3. **Given** an administrator abandons a creation session before it is complete, **When** the session ends without all required elements supplied, **Then** no story configuration is persisted from that attempt.
4. **Given** an administrator wants to try again after an abandoned session, **When** they start a new creation session, **Then** it begins fresh and does not attempt to resume the abandoned one.

---

### Edge Cases

- An administrator provides contradictory answers across the conversation (e.g., changes the setting partway through): the system reflects the most recent answer for that element in the generated configuration.
- An administrator supplies only a single character type: the system accepts it — a story is not required to offer more than one character type, though offering a choice is expected to be the common case.
- The LLM's generated configuration is incomplete or malformed despite sufficient administrator input: the system does not persist a broken configuration and instead surfaces the problem to the administrator for another attempt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to start a new story-creation session and describe their idea in plain, natural language.
- **FR-002**: System MUST present the story-creation experience as a wizard with steps for name & cover, world & setting, tone & reading level, and session length, reachable in any order, and MUST ask guiding questions within that flow to elicit, at minimum, a story's setting/plot, its character types, and its completion criteria.
- **FR-003**: System MUST use an LLM to generate a complete story configuration once the administrator has supplied sufficient detail across all required elements.
- **FR-004**: System MUST automatically persist a generated story configuration once it is complete, without requiring a separate manual save action.
- **FR-005**: System MUST NOT persist any story configuration from a creation session the administrator abandons before it is complete.
- **FR-006**: A newly created story configuration MUST default to unpublished, so it is not visible to players until an administrator explicitly publishes it (see `005-story-publishing`).
- **FR-007**: Each distinct step of the story-creation conversation (eliciting setting/plot, eliciting character types, eliciting completion criteria, generation, persistence, abandonment) MUST have a corresponding automated test verifying its expected behavior.
- **FR-008**: System MUST provide dedicated fields — within the existing wizard steps or an additional step — for the administrator to define one or more character types and the story's completion criteria: an optional maximum session duration, one or more success conditions, optionally one or more failure conditions, and — when more than one condition is defined — a rule for whether any one or all of them must be met to end the game (this shape is enforced during play by `008-core-gameplay`). These MUST NOT be captured only as unstructured free text embedded in another field's prose.

### Key Entities

- **Story**: A complete adventure narrative — setting, character types, plot, and completion criteria — along with whatever guidance is needed to keep the LLM's later narration consistent with it. Newly created in an unpublished state (see `005-story-publishing`).
- **Story-Creation Exchange**: A single turn in the conversation between an administrator and the system while building a Story — the atomic unit of the elicitation process.
- **Character Type**: An option, scoped to the Story being created, that a player will later choose from when setting up a new game against it (see `006-adventure-and-character-setup`).
- **Completion Criteria**: The conditions authored for a Story that determine when a play session ends — an optional maximum duration, one or more success conditions, and optionally one or more failure conditions, together with a rule for whether any one or all configured conditions must be met when more than one is defined. Authored here; enforced during play by `008-core-gameplay`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator with no prior training can go from starting a creation session to having a complete, persisted story within a single sitting, using natural language alone (no direct editing of structured data or code).
- **SC-002**: 100% of abandoned creation sessions in testing result in no story being persisted.
- **SC-003**: 100% of completed creation sessions in testing produce a story configuration with at least one character type and at least one completion criterion.

## Assumptions

- This spec covers only the guided/conversational creation path. Direct upload of a pre-built configuration file is a separate capability (see `011-story-import`).
- Making a created story visible to players is a separate, explicit action, not part of this feature (see `005-story-publishing`).
- There is no requirement to resume an abandoned creation session; an administrator who wants to try again starts a fresh session.
- There is no defined limit on the number of stories an administrator may create.
- An administrator may have multiple story-creation sessions in progress concurrently; starting a new session does not require completing or abandoning any other in-progress session.
- Tone, reading level, target session length, and chapter count are collected by the wizard steps in scope for this feature (per the design reference) but are deliberately left undocumented as Key Entity attributes here; naming them is deferred to a later spec/pass (see `specs/designs/README.md`'s tracked gap).
