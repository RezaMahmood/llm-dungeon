---

description: "Task list for A Player-Authored Avatar Replaces the Character-Type Picker"
---

# Tasks: A Player-Authored Avatar Replaces the Character-Type Picker

**Input**: Design documents from `/specs/032-story-archetypes-player-avatar/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — Constitution Principle I and FR-030 require an automated test for every
behaviour this feature introduces or changes.

**Organization**: Three user stories (US1 P1, US2 P2, US3 P2) plus Foundational work (the new
container, the widened models, the new validation service) that every story needs, plus a
Specification Hygiene phase for the six sibling specs (FR-029) and Polish.

## Path Conventions

Existing web-application layout: `src/backend/`, `src/frontend/`. Infra: `infrastructure/terraform/`.

---

## Phase 1: Setup

No setup task is needed. The backend/frontend projects, their test runners, and Terraform tooling
already exist and require no initialization for this slice.

## Phase 2: Foundational

**Purpose**: Infrastructure and model/service scaffolding every user story depends on.

- [X] T001 Add `azurerm_cosmosdb_sql_container.avatar_setup_attempts` (name
      `avatarSetupAttempts`, partition key `/id`, mirroring `test_play_sessions`/
      `player_content_safety_standings`) in `infrastructure/terraform/main.tf`, plus its
      `AVATAR_SETUP_ATTEMPTS_CONTAINER` app setting alongside the other container settings
      (data-model.md "AvatarSetupAttempts")
- [X] T002 Add `AVATAR_SETUP_ATTEMPTS_CONTAINER = "avatarSetupAttempts"` to
      `src/backend/config.py`, mirroring the existing container-constant list (research.md
      Decision 3)
- [X] T003 [P] Create `AvatarSetupAttempts` model (`id`, `playerId`, `storyId`,
      `modelBackedAttempts`, `entityType`) with `to_dict`/`from_dict` in
      `src/backend/models/avatar_setup_attempts.py` (data-model.md)
- [X] T004 [P] Widen `PlaySession.characterType` to `Optional[str] = None` and add
      `avatarDescription: Optional[str] = None` in `src/backend/models/play_session.py`,
      updating `to_dict`/`from_dict` (`characterType` via `.get`, not `[...]`) (data-model.md,
      FR-025, FR-026)
- [X] T005 [P] Apply the same widening to `TestPlaySession` in
      `src/backend/models/test_play_session.py` (data-model.md)
- [X] T006 Create `AvatarSetupAttemptsService` (`get_or_create`, `increment`, `delete`, bounded
      3-attempt `_etag` read-modify-write, mirroring
      `PlayerContentSafetyStandingService`/`StoryService.record_test_play`) in
      `src/backend/services/avatar_setup_attempts_service.py` (research.md Decision 3, depends
      on T001-T003)

**Checkpoint**: The new container, models, and attempt-tracking service exist; no user story
depends on anything else before starting.

---

## Phase 3: User Story 1 - A Player Describes Their Own Character (Priority: P1) 🎯 MVP

**Goal**: A player is required to write a free-text avatar description (20–500 characters,
validated for story-relevance and injection resistance) instead of picking a character type; it
becomes their identity in the narration from turn 1 onward, with turn 0 unaffected.

**Independent Test**: Set up a new game, enter a character name and an avatar description, start
play, and verify the narration reflects the described character from turn 1 while turn 0 is
byte-identical to the authored opening — with no character-type choice offered anywhere.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; confirm they FAIL before implementation.

- [X] T007 [P] [US1] Add tests asserting the cost-free checks (blank, <20 chars, >500 chars)
      reject with no model call, in `src/backend/tests/unit/test_avatar_validation_service.py`
      (FR-006, FR-010, SC-006, SC-009)
- [X] T008 [P] [US1] Add tests asserting an instruction-shaped description and a suite of known
      prompt-injection patterns are rejected by the model-backed check, in the same file
      (FR-007, FR-008, SC-007)
- [X] T009 [P] [US1] Add tests asserting a timeout (mocked to exceed 10s) and a mocked call
      error both reject as "no verdict" with distinguishable messaging, in the same file
      (FR-011, FR-012, SC-008)
- [X] T010 [P] [US1] Add tests asserting `AvatarSetupAttemptsService` increments only on a
      model-backed attempt, caps at the configured limit with a plain-language message, and is
      cleared on successful session creation, in
      `src/backend/tests/unit/test_avatar_setup_attempts_service.py` (FR-014, SC-011)
- [X] T011 [P] [US1] Add a test asserting a validation call's tokens land on `Story.totalTokens`
      and no `PlaySession.totalTokens`, rejections included, in
      `src/backend/tests/unit/test_story_service.py` (FR-016, SC-013)
- [X] T012 [P] [US1] Add tests asserting `create_session` requires `avatarDescription`,
      identifies exactly which of adventure/name/avatar is missing, and no longer accepts or
      requires `characterType`, in `src/backend/tests/unit/test_play_session_service.py`
      (FR-001, FR-002, FR-004, SC-002, SC-003)
- [X] T013 [P] [US1] Add tests asserting the built gameplay-turn prompt carries the avatar
      description as the player's identity on every turn, and that turn 0 remains verbatim and
      avatar-independent, in `src/backend/tests/unit/test_llm_service.py` (FR-018, FR-019,
      FR-021, SC-004, SC-005)
- [X] T014 [P] [US1] Add a frontend test asserting `AvatarDescriptionStep` renders no
      character-type choice, shows a pending indication with no countdown while checking, and
      disables resubmission meanwhile, in
      `src/frontend/tests/components/GameSetup/AvatarDescriptionStep.test.jsx` (FR-002, FR-013,
      SC-003)
- [X] T015 [P] [US1] Add a frontend test asserting `GamePage` retains the character name and
      does not discard typed avatar text when the selected adventure changes, in
      `src/frontend/tests/pages/GamePage.test.jsx` (FR-005)

### Implementation for User Story 1

- [X] T016 [US1] Implement `AvatarValidationService` — cost-free checks then the model-backed
      check behind `asyncio.wait_for(..., timeout=10)`, fail-closed on timeout/error — in
      `src/backend/services/avatar_validation_service.py` (depends on T007-T009 failing first;
      research.md Decision 2)
- [X] T017 [US1] Add the token-accrual method to `StoryService` mirroring `record_test_play`, in
      `src/backend/services/story_service.py` (depends on T011; research.md Decision 4)
- [X] T018 [US1] Wire `AvatarValidationService` and `AvatarSetupAttemptsService` into
      `PlaySessionService.create_session`, replacing the `characterType` validation block with
      avatar-description validation, in `src/backend/services/play_session_service.py`
      (depends on T004, T006, T016, T017)
- [X] T019 [US1] Change `_build_gameplay_turn_prompt`'s `Character:` line to use
      `session.avatarDescription`, falling back to the name alone when `None`, in
      `src/backend/services/llm_service.py` (depends on T004, T013; research.md Decision 5)
- [X] T020 [US1] Update `src/backend/api/game/sessions.py` to accept `avatarDescription` in the
      setup request body and map new error fields to the response shape (depends on T018)
- [X] T021 [US1] Create `AvatarDescriptionStep.jsx` (textarea, length hint, pending/disabled
      affordance from the design system) replacing `CharacterTypeStep.jsx`, in
      `src/frontend/src/components/GameSetup/` (depends on T014; research.md Decision 7)
- [X] T022 [US1] Update `GamePage.jsx` to hold `avatarDescription` setup state instead of
      fetching/passing `characterTypes` into a picker, retaining it across an adventure change
      (depends on T015, T021)
- [X] T023 [US1] Delete `CharacterTypeStep.jsx` and its test (superseded by T021)
- [X] T024 [US1] Run `pytest -k avatar` and `pytest tests/unit/test_llm_service.py -k
      gameplay_turn_prompt` from `src/backend`, and `npm run test -- AvatarDescriptionStep
      GamePage` from `src/frontend`, and confirm T007-T015 now pass (depends on T016-T023)

**Checkpoint**: A new game can be set up entirely without a character-type choice, with the
avatar description validated, carried on the session, and reflected in the narration from turn 1.

---

## Phase 4: User Story 2 - An Administrator Authors a Cast, Not a Class List (Priority: P2)

**Goal**: The roster is presented to administrators as story-world cast material, not a
player-selectable class list, and test play uses a fixed tester avatar rather than deriving one.

**Independent Test**: Walk the authoring wizard and configuration viewer and verify no wording
implies player selection; run a test play and verify it starts with a fixed tester avatar and no
derived character type.

### Tests for User Story 2 ⚠️

- [X] T025 [P] [US2] Add a test asserting `create_session` (test play) sets a fixed
      `avatarDescription` constant and no `characterType`, in
      `src/backend/tests/unit/test_test_play_session_service.py` (FR-024)
- [X] T026 [P] [US2] Update `src/frontend/tests/components/StoryWizard/CharacterTypeList.test.jsx`
      to assert cast-framed labels/help text with no player-selection wording (FR-023, SC-016)

### Implementation for User Story 2

- [X] T027 [US2] Add `TESTER_AVATAR_DESCRIPTION` constant and use it in place of
      `characterType=story.characterTypes[0].name` in
      `src/backend/services/test_play_session_service.py` (depends on T005, T025; research.md
      Decision 6)
- [X] T028 [US2] Update the test-play API response in `src/backend/api/admin/test_play.py` to
      stop exposing `characterType` (depends on T027)
- [X] T029 [US2] Reword labels/help text in
      `src/frontend/src/components/Admin/StoryWizard/CharacterTypeList.jsx` to describe the
      story's cast, with no player-selection wording (depends on T026; FR-023)
- [X] T030 [US2] Run `pytest -k avatar` in `src/backend` and `npm run test --
      CharacterTypeList` in `src/frontend` and confirm T025-T026 now pass (depends on
      T027-T029)

**Checkpoint**: The roster reads as cast throughout authoring/editing/import/review, and test
play never derives a character type.

---

## Phase 5: User Story 3 - Games Already in Progress Keep Working (Priority: P2)

**Goal**: A session saved before this change resumes and plays on without error, keeping its
character name, dropping its old character type, and never being asked for an avatar description.

**Independent Test**: Resume a session fixture shaped like a pre-change document (has
`characterType`, no `avatarDescription`) and take a turn; verify no error, no avatar-description
prompt, and the character name still reaches the narration.

### Tests for User Story 3 ⚠️

- [X] T031 [P] [US3] Add a test loading a pre-change-style `PlaySession` fixture (`characterType`
      present, no `avatarDescription` key) through `from_dict` and asserting no error and
      `avatarDescription is None`, in `src/backend/tests/unit/test_play_session_service.py`
      (FR-025, FR-026)
- [X] T032 [P] [US3] Add a test asserting a resumed pre-change session's built prompt supplies
      the character name alone (no avatar description, no character type) as the player's
      identity, in `src/backend/tests/unit/test_llm_service.py` (FR-027, SC-014)
- [X] T033 [P] [US3] Add a test asserting resuming such a session never triggers an
      avatar-description prompt or validation call, in
      `src/backend/tests/unit/test_play_session_service.py` (FR-028)

### Implementation for User Story 3

- [X] T034 [US3] Confirm (and adjust if needed) that the resume/interaction-submission path in
      `src/backend/services/play_session_service.py` requires no changes beyond T004's model
      widening — no avatar-description gate on an already-existing session (depends on T004,
      T031-T033)
- [X] T035 [US3] Run `pytest -k "resume or pre_change"` from `src/backend` and confirm T031-T033
      pass (depends on T034)

**Checkpoint**: Every pre-existing saved session keeps working exactly as SC-014 requires.

---

## Phase 6: Specification Hygiene (FR-029)

- [X] T036 [P] Amend `specs/006-adventure-and-character-setup/spec.md`: FR-003, FR-003a, FR-004,
      FR-004a, the Character Type key entity, SC-001, SC-002 — remove the player-chooses-a-type
      model
- [X] T037 [P] Amend `specs/004-story-creation-done/spec.md`'s Character Type key entity to drop
      "a player will later choose from"
- [X] T038 [P] Amend `specs/008-core-gameplay-done/spec.md`'s Independent Test line and
      session-setup reference, and its `data-model.md`'s `characterType` row and
      validation-trust note
- [X] T039 [P] Amend `specs/009-save-and-continue/data-model.md`'s resume-carried-fields note to
      reflect `avatarDescription`/dropped `characterType`
- [X] T040 [P] Amend `specs/010-story-test-play-done/spec.md`'s Independent Test wording and its
      `research.md` "Decision 6" tester-derivation rationale
- [X] T041 [P] Amend `specs/012-story-editing-and-review/spec.md`'s FR-004 roster-export wording
      to the cast framing

**Checkpoint**: No shipped spec still states or implies the player-selects-a-type model.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T042 Run the full backend suite (`pytest` from `src/backend`) and confirm it is green
- [X] T043 Run the full frontend suite (`npm run test` from `src/frontend`) and confirm it is
      green
- [X] T044 Run `quickstart.md`'s validation commands and confirm the expected outcomes match
      what T007-T033 assert
- [X] T045 `terraform validate` (or the project's existing equivalent check) against
      `infrastructure/terraform/main.tf` for the new container resource (depends on T001)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: None needed.
- **Foundational (Phase 2)**: No dependency; MUST complete before any user story starts (T001-T006
  are shared: the container, the models, the attempt-tracking service).
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational (T005 specifically). Independent of US1's
  outcome, though it touches an adjacent file (`test_play_session_service.py`).
- **User Story 3 (Phase 5)**: Depends on Foundational (T004 specifically). Independent of
  US1/US2.
- **Specification Hygiene (Phase 6)**: Independent of all code phases; may run any time after
  Phase 2, in parallel with Phases 3-5.
- **Polish (Phase 7)**: Depends on Phases 3, 4, and 5 all completing.

### Within Each User Story

- Tests MUST be written and confirmed failing before that story's implementation tasks.
- Within US1: T016 (validation service) and T017 (token accrual) before T018 (wiring); T019
  (prompt) can run in parallel with T016-T018; frontend tasks T021-T023 depend only on T014/T015,
  not on the backend tasks.

### Parallel Opportunities

- All of T007-T015 (US1 tests, distinct files) in parallel.
- T025-T026 (US2 tests) in parallel; T031-T033 (US3 tests) in parallel.
- All of Phase 6 (T036-T041, six distinct spec files) in parallel, and in parallel with Phases
  3-5 once Phase 2 is done.

---

## Implementation Strategy

### MVP = User Story 1

Complete Phase 2 (Foundational), then Phase 3 (US1) in full: write T007-T015, confirm they fail,
implement T016-T023, verify via T024. This alone delivers the player-facing change the issue is
named for.

### Incremental delivery

1. Foundational → US1 (MVP: avatar replaces the picker, validated, in the narration).
2. US2 (cast wording, fixed tester avatar) and US3 (resume compatibility) can each follow
   independently, in either order, and in parallel with Phase 6's spec amendments.
3. Polish closes with the full-suite regression check and a Terraform validation pass, since this
   slice's Cosmos/Terraform change places it in the constitution's persisted-data blast-radius
   category regardless of code-diff size.

---

## Phase 8: Convergence

Appended by `/speckit-converge` after assessing the merged implementation against this
feature's spec, plan, and tasks. Ordered CRITICAL first.

- [ ] T046 Make the model-backed attempt cap recoverable: `AvatarSetupAttempts` is cleared only
      on successful session creation (`play_session_service.py:279`), but `validate_relevance`
      raises `AvatarValidationAttemptsExceededError` before any check once
      `modelBackedAttempts >= MAX_MODEL_BACKED_ATTEMPTS`, and the container carries no TTL — so a
      player who reaches the cap can never create a session for that adventure again, and the
      429's "Take a short break and try again" promises a recovery that cannot happen. Give the
      counter a time window (or an equivalent reset) so a break genuinely clears it, and cover it
      with a test, per FR-014, SC-011 and the Edge Case "they are ... not left without a next
      action" (contradicts) — CRITICAL
- [ ] T047 Add the second, independent line of defence against injection in the avatar
      description: `_build_gameplay_turn_prompt` (`llm_service.py:540`) interpolates it into the
      trusted configuration block beside `World:`/`Rules:`/`Narrative guidance:`, and
      `gameplay_turn_system_prompt.txt` hardens only "Player's latest input" — leaving the FR-007
      model-backed check as the sole defence. Label the avatar as player-supplied in the prompt
      and instruct the narrator never to treat it as an instruction, mirroring the existing
      player-input clause, per FR-008 and SC-007 (missing)
- [ ] T048 Stop recording avatar description text in telemetry:
      `llm_service.py:315` sets `span.set_attribute("gen_ai.prompt", description)` before the
      verdict is known, so every description — rejected ones and judged injection attempts
      included — is durably captured in traces, per FR-015 and SC-012 (contradicts)
- [ ] T049 Amend `specs/006-adventure-and-character-setup/data-model.md` (lines 21, 33, 61, 72,
      92-93) and `specs/006-adventure-and-character-setup/contracts/api.md` (lines 93, 103, 115,
      125, 147), which still declare `characterType` **Required**, validated against the
      adventure's roster, with the error `"Select a character type for this adventure."` — T036
      amended only that feature's `spec.md`, though FR-029 names "its data model and contracts"
      (missing)
- [ ] T050 Add the avatar test coverage FR-030 requires but that does not exist: a suite of known
      context/prompt-injection patterns; a test that an accepted-but-hostile description cannot
      override the narration (T047's defence); and a test that no rejected description text
      reaches the exported spans (T048's fix, using the existing `otel_exporters` fixture in
      `tests/conftest.py`). The current
      `test_instruction_shaped_description_is_rejected` mocks the verdict and so exercises
      plumbing only, per FR-030, SC-007 and SC-012 (missing)
- [ ] T051 Reword the remaining roster surfaces to the cast framing — the import validator
      (`src/backend/services/story_config_file.py:139,197,202,209` and
      `src/frontend/src/components/Admin/StoryConfigUpload.jsx:30`) and the wizard's
      completeness message (`src/frontend/src/pages/AdminStoryWizardPage.jsx:121`), all of which
      still read "at least one character type" — per FR-023, which names import explicitly, and
      SC-016 (partial)
- [ ] T052 Review and justify or remove `characterTypes` from the player-facing
      `GET /game/adventures/{adventureId}` response (`src/backend/api/game/adventures.py`): it is
      a leftover of the deleted picker, is consumed nowhere in the frontend, and ships the
      story's cast to the player client, while
      `test_get_adventure_returns_character_types_for_published_story` locks the behaviour in,
      per FR-002 and FR-022 (unrequested)
