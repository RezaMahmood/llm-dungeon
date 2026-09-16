---

description: "Task list for The Story's Cast Reaches the Narration"
---

# Tasks: The Story's Cast Reaches the Narration

**Input**: Design documents from `/specs/033-story-cast-in-narration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — Constitution Principle I requires an automated test for every behaviour,
and FR-006 names the four behaviours this slice must cover.

**Organization**: This spec has a single user story (P1), so there is one implementation phase
after Setup/Foundational (both already satisfied by the existing codebase — no new task needed
for either).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps the task to the user story it belongs to (US1)

## Path Conventions

Existing web-application layout: backend code and tests under `src/backend/`. This slice touches
only `src/backend/services/llm_service.py` and `src/backend/tests/unit/test_llm_service.py`.

---

## Phase 1: Setup

No setup task is needed. The backend project, its test runner, and its fixtures already exist and
require no initialization for this slice.

## Phase 2: Foundational

No foundational task is needed. `CharacterType` (name + optional description), `Story.characterTypes`,
and its "at least one entry" validation already exist unchanged (data-model.md) and require no new
scaffolding before User Story 1 can be built.

---

## Phase 3: User Story 1 - The Story's Cast Reaches the Narration (Priority: P1) 🎯 MVP

**Goal**: An adventure's authored roster is supplied to the narration as the story world's cast —
distinctly labelled, descriptions included, taking precedence over invented characters for named
or story-significant roles — with every pre-existing roster still valid (FR-001 through FR-006).

**Independent Test**: Author an adventure with several distinct roster entries, build a gameplay
turn prompt, and verify the prompt contains a distinctly labelled cast block (separate from the
player's own character line) with descriptions attached, plus a precedence instruction; verify a
pre-change-style roster still builds a valid prompt unchanged.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; confirm they FAIL before implementation.

- [X] T001 [P] [US1] Add test asserting the built gameplay-turn prompt contains a cast block
      listing every `CharacterType` on the story, distinctly labelled and separate from the
      `Character: {name} ({type})` player line, in
      `src/backend/tests/unit/test_llm_service.py` (covers Acceptance Scenario 1, FR-001, SC-001)
- [X] T002 [P] [US1] Add test asserting a `CharacterType` with a `description` renders that
      description in the cast block, and one with no description renders by name alone, in
      `src/backend/tests/unit/test_llm_service.py` (covers Acceptance Scenario 4, Edge Case,
      FR-001)
- [X] T003 [P] [US1] Add test asserting the built prompt contains an instruction directing the
      narration to prefer a fitting roster entry over inventing a named or story-significant
      character, in `src/backend/tests/unit/test_llm_service.py` (covers Acceptance Scenario 2,
      FR-002)
- [X] T004 [P] [US1] Add test using a pre-change-style `Story` fixture (roster entries read like
      player classes, e.g. "Warrior", "Scout", no descriptions) asserting the prompt still builds
      successfully with that roster present as cast and no error raised, in
      `src/backend/tests/unit/test_llm_service.py` (covers Acceptance Scenario 5, Edge Case,
      FR-004, SC-003)

### Implementation for User Story 1

- [X] T005 [US1] In `_build_gameplay_turn_prompt` (`src/backend/services/llm_service.py`), after
      the existing `Character: {name} ({type})` line, render a distinctly labelled cast block from
      `story.characterTypes`, including each entry's `description` where authored and the name
      alone where it is not (depends on T001-T004 failing first)
- [X] T006 [US1] In the same method, add the precedence instruction directing the narration to
      draw a named or story-significant character from the cast whenever an entry fits, leaving
      incidental background figures and unfitting moments open to invention (depends on T005)
- [X] T007 [US1] Run `pytest tests/unit/test_llm_service.py -k gameplay_turn_prompt` from
      `src/backend` and confirm T001-T004 now pass (depends on T005, T006)

**Checkpoint**: User Story 1 is fully functional and independently testable — the cast reaches the
narration, descriptions travel, precedence is instructed, and every pre-existing roster still
works.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T008 Run the full backend suite (`pytest` from `src/backend`) and confirm it is green,
      verifying FR-005 — no other backend behaviour changed
- [X] T009 Run `quickstart.md`'s validation commands and confirm the expected outcomes there match
      what T001-T004 assert

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: None needed (see Phase 1 and 2 above) — User Story 1 can start
  immediately.
- **User Story 1 (Phase 3)**: The only story; no dependency on another story.
- **Polish (Phase 4)**: Depends on Phase 3 completing.

### Within User Story 1

- T001-T004 (tests) MUST be written and confirmed failing before T005-T006 (implementation).
- T005 before T006 (the cast block exists before the instruction is added alongside it).
- T007 depends on T005 and T006 both being in place.

### Parallel Opportunities

- T001, T002, T003, T004 are all in the same file but test independent behaviours with no shared
  dependency on incomplete code — they may be written in parallel, then run together.

---

## Parallel Example: User Story 1

```bash
# Write all four tests for User Story 1 together (same file, independent assertions):
Task: "Add cast-block test in src/backend/tests/unit/test_llm_service.py"
Task: "Add description-travels test in src/backend/tests/unit/test_llm_service.py"
Task: "Add precedence-instruction test in src/backend/tests/unit/test_llm_service.py"
Task: "Add pre-existing-roster test in src/backend/tests/unit/test_llm_service.py"
```

---

## Implementation Strategy

### MVP = the whole slice

There is one user story, so the MVP is Phase 3 in full: write T001-T004, confirm they fail, then
implement T005-T006 and confirm T001-T004 pass via T007. Phase 4 is a regression check before
opening the pull request.

---

## Phase 5: Convergence

- [ ] T010 CRITICAL: Add a test asserting a story whose roster has a single `CharacterType`
      still builds a prompt whose cast block carries that entry and whose precedence
      instruction leaves incidental background figures open to invention, in
      `src/backend/tests/unit/test_llm_service.py` per Constitution I and the spec Edge Case
      "a roster has a single entry and the story calls for a crowd" (missing)
- [ ] T011 CRITICAL: Strengthen the two weak assertions in
      `src/backend/tests/unit/test_llm_service.py` so they exercise real behaviour per
      Constitution I: in `test_gameplay_turn_prompt_supplies_the_roster_as_cast_distinct_from_the_player`
      replace `cast_line_index != character_line_index` (which no line can violate, since a
      line cannot start with both `Character:` and `Cast:`) and the prompt-wide `in` checks
      with assertions that each roster entry is rendered inside the `Cast:` block itself; in
      `test_gameplay_turn_prompt_directs_precedence_of_roster_over_invented_characters` replace
      `"prefer" in prompt.lower()` / `"cast" in prompt.lower()` with an assertion on the
      precedence instruction's substance (partial)
- [ ] T012 In `src/backend/services/prompts/gameplay_turn_system_prompt.txt`, name the cast
      block among the supplied story configuration the narrator is told to read (currently
      "worldPrompt, rules, narrativeGuidance, tone, readingLevel" only) so the narrator's own
      instructions acknowledge the cast and its precedence rule, per FR-001 and FR-002
      (partial)
- [ ] T013 Run `pytest tests/unit/test_llm_service.py -k gameplay_turn_prompt` and then the full
      `pytest` suite from `src/backend`, confirming T010-T011 pass and nothing else regressed
      (depends on T010-T012)
