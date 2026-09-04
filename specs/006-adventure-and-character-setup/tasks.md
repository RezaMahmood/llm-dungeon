---

description: "Task list for Adventure and Character Setup (006-adventure-and-character-setup)"
---

# Tasks: Adventure and Character Setup

**Input**: Design documents from `/specs/006-adventure-and-character-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle I (NON-NEGOTIABLE) and spec.md FR-007
both require an automated test for every functional requirement and edge case in this feature.

**Organization**: This feature has a single user story (US1, P1) per spec.md. Tasks are grouped
by phase: Setup → Foundational → **UI Design Sign-off (Constitution Principle XI gate)** →
User Story 1 → Polish (including the Principle IX final acceptance task).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 for all User Story 1 tasks
- File paths are exact, per plan.md's Project Structure

---

## Phase 1: Setup

**Purpose**: No new project scaffolding, dependencies, or tooling is required — this feature
reuses the existing `src/backend/api/game/`, `src/backend/services/`, `src/frontend/src/pages/`,
and `src/frontend/src/services/` trees as-is (plan.md Project Structure). Skipped as a distinct
phase; the first new files are created directly in Phase 2 (Foundational).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared authorization plumbing both the new endpoint and the extended endpoint
depend on. MUST complete before any User Story 1 task.

- [X] T001 [P] Unit test `authorize_player` (valid Player token → authorized; non-Player role →
  `forbidden_insufficient_permission`; non-allow-listed → `forbidden_access_not_granted`; no/invalid
  token → `unauthorized`), mirroring `src/backend/tests/unit/test_admin_capability.py`'s
  structure, in `src/backend/tests/unit/test_game_middleware.py`
- [X] T002 Implement `authorize_player` in `src/backend/api/game/middleware.py`, mirroring
  `src/backend/api/admin/middleware.py::authorize_admin` exactly but checking for `"Player"` in
  `entry.roles` (research.md Decision 3); makes T001 pass

**Checkpoint**: `authorize_player` exists and is tested — User Story 1 work can begin.

---

## Phase 3: UI Design Sign-off (Constitution Principle XI Gate — NON-NEGOTIABLE)

**Purpose**: Principle XI requires the screen design for any new user-facing UI to be explicitly
agreed with the requesting user/product owner *before* implementation starts. `plan.md`'s
Constitution Check flagged this as an open gap: `specs/designs/02-story-select.html` covers only
the adventure-list step; the character-name-entry and character-type-selection steps have no
existing mockup. This phase MUST be complete before any Phase 4 (User Story 1) frontend
implementation task begins. Backend-only tasks (T001–T002, and the backend portion of Phase 4)
are not blocked by this phase, since they carry no UI.

- [X] T003 Produce a mockup/wireframe (extending `specs/designs/02-story-select.html`'s "Start
  something new" card-list step) for the two new steps — character name entry and character
  type selection — using only this project's existing design-token layer and shared component
  classes (Constitution Principle VIII: form field, and a radio-card/segmented-control pattern
  for character type choice), plus the adventure-list step's presentation of the "no adventures
  published" empty state (FR-006) and the missing-fields message (FR-005). Save it under
  `specs/designs/` (e.g. `specs/designs/06-game-setup.html`) alongside the existing screens, and
  reference it from `specs/designs/README.md`.
- [X] T004 Obtain and record the requesting user's/product owner's explicit sign-off on T003's
  design (per Principle XI, a design artifact existing is not sufficient — confirmation is
  required). Do not begin T015 or any later frontend task until this is confirmed.

  **Sign-off record**: Design `specs/designs/06-game-setup.html` reviewed and approved by
  the requesting product owner on 2026-09-04, confirmed during `/speckit-analyze` remediation.

**Checkpoint**: Design agreed and confirmed — User Story 1 frontend implementation may begin.

---

## Phase 4: User Story 1 - Player Selects an Adventure and Creates a Character (Priority: P1) 🎯 MVP

**Goal**: A player picks a published adventure, enters a character name, and picks a character
type defined for that adventure; play cannot start until all three are valid (spec.md
Acceptance Scenarios 1–5).

**Independent Test**: With one published adventure defining ≥2 character types, select the
adventure, enter a character name, choose a character type, and verify play is only confirmed
as ready after all three are supplied and valid (spec.md's Independent Test).

### Tests for User Story 1 (write first; MUST fail before implementation)

- [X] T005 [P] [US1] Unit test `Story`-list-to-`AdventureSummary` filtering/shaping logic (only
  `published == true` rows returned; correct field subset — FR-001, FR-006) in
  `src/backend/tests/unit/test_story_service.py` (extend existing file) or a new
  `src/backend/tests/unit/test_game_adventures_summary.py` if the logic lives outside
  `StoryService`
- [X] T006 [P] [US1] Unit test `POST /api/game/start` field validation logic — blank/whitespace
  name rejected, name >50 chars rejected, missing/unknown `characterType` rejected, `characterType`
  valid for a *different* adventure rejected, all-valid accepted (FR-002, FR-003, FR-003a,
  FR-004a, edge cases) in `src/backend/tests/unit/test_game_start_validation.py`
- [X] T007 [P] [US1] Integration test `GET /api/game/adventures`: authorized Player sees only
  published adventures with the `AdventureSummary` shape (contracts/api.md); zero published
  adventures → `200` with `adventures: []`; non-Player caller → `403`; unauthenticated → `401`
  (FR-001, FR-006) in `src/backend/tests/integration/test_game_adventures_endpoint.py`
- [X] T008 [P] [US1] Integration test `GET /api/game/adventures/{adventureId}`: published
  adventure → `200` with its `characterTypes`; unpublished or nonexistent id → identical `404`
  (contracts/api.md) in `src/backend/tests/integration/test_game_adventures_endpoint.py`
  (same file as T007, additional test functions)
- [X] T009 [P] [US1] Integration test `POST /api/game/start`: complete valid setup → `200` with
  echoed fields; each of the 400 field-error cases from contracts/api.md (missing/blank/too-long
  name, missing/foreign-adventure character type); unpublished/nonexistent `adventureId` → `404`
  (FR-002 through FR-005) in `src/backend/tests/integration/test_game_start_endpoint.py` (extend
  existing file/tests)

### Backend implementation for User Story 1

- [X] T010 [US1] Add a published-only, `AdventureSummary`-shaped query method to
  `src/backend/services/story_service.py` (e.g. `list_published_summaries()`), filtering on
  `published == true` and selecting `id, name, tone, sessionLengthMinutes, readingLevel`
  (data-model.md AdventureSummary; depends on T005 existing and failing)
- [X] T011 [US1] Implement `GET /api/game/adventures` and `GET /api/game/adventures/{adventureId}`
  handlers in `src/backend/api/game/adventures.py`, using `authorize_player` (T002) and
  `StoryService` (T010 for the list; `get_story` + a `published` check, returning the shared
  `not_found` response for unpublished-or-missing, for the detail route) — makes T007 and T008
  pass
- [X] T012 [US1] Register the two new routes in `src/backend/function_app.py`
  (`GET manage-style` player routes: `game/adventures` and `game/adventures/{adventureId}`),
  following the existing `_guarded(...)` wrapper pattern used for `game/start` and the admin
  routes
- [X] T013 [US1] Extend `src/backend/api/game/start.py::start` to replace `authorize_player`'s
  inline duplicate check with a call to the new `authorize_player` (T002), parse
  `{adventureId, characterName, characterType}` from the request body, and validate per
  contracts/api.md (adventure exists+published → else `404`; name trimmed non-blank ≤50 chars;
  characterType present in that adventure's `characterTypes` names; collect and return every
  failing field under `fields` on `400`) — makes T006 and T009 pass; still returns the existing
  `200` "success" shape (now echoing the three fields) rather than creating a play session
  (research.md Decision 4)

### Frontend implementation for User Story 1

*(T015–T018 are blocked until Phase 3's T004 sign-off is confirmed — they render the agreed
design. T014 is design-independent (pure API wiring against contracts/api.md) and is NOT
blocked by T004; it only needs T011/T013's routes to exist.)*

- [X] T014 [P] [US1] Add `listAdventures(token)`, `getAdventure(token, adventureId)`, and
  `startGame(token, { adventureId, characterName, characterType })` functions to a new
  `src/frontend/src/services/gameService.js`, following `src/frontend/src/services/
  accountService.js`'s `axios` + bearer-token pattern
- [X] T015 [US1] Build the `AdventureList` step component in
  `src/frontend/src/components/GameSetup/AdventureList.jsx`, matching the design agreed in T003
  (card list per `02-story-select.html`'s "Start something new" pattern), calling
  `listAdventures` on mount and rendering the FR-006 empty-state message when the list is empty
- [X] T016 [US1] Build the `CharacterNameStep` component in
  `src/frontend/src/components/GameSetup/CharacterNameStep.jsx`, matching T003's design: a
  design-system text field, client-side hint validation (non-blank, ≤50 chars) mirroring the
  server rule from T013, shown only after an adventure is selected (FR-003a)
- [X] T017 [US1] Build the `CharacterTypeStep` component in
  `src/frontend/src/components/GameSetup/CharacterTypeStep.jsx`, matching T003's design: fetches
  the selected adventure's `characterTypes` via `getAdventure` and presents them as an explicit
  choice (a single type is still shown as a one-option choice, not auto-selected — edge case),
  shown only after an adventure is selected (FR-003a)
- [X] T018 [US1] Rebuild `src/frontend/src/pages/GamePage.jsx` to orchestrate the three steps in
  order (adventure → name → type per FR-003a), holding `adventureId`/`characterName`/
  `characterType` in local state; clear `characterType` (retain `characterName`) whenever
  `adventureId` changes (FR-004a); disable/block the final "start" action and surface which
  field(s) are missing/invalid (from client-side checks and from `startGame`'s `400 fields`
  response) until `startGame` succeeds (FR-004, FR-005)
- [X] T019 [P] [US1] Component tests for `AdventureList`, `CharacterNameStep`, and
  `CharacterTypeStep` (empty-state rendering, name length/blank rejection, type list rendering
  and single-type-still-a-choice behavior) in `src/frontend/tests/components/GameSetup/`,
  following `src/frontend/tests/integration/admin_accounts.test.jsx`'s RTL patterns
- [X] T020 [US1] Integration test for the full `GamePage` flow (select adventure → enter name →
  choose type → blocked-until-complete → successful start), mocking `gameService` per
  `src/frontend/tests/integration/admin_story_creation_flow.test.jsx`'s pattern, in
  `src/frontend/tests/integration/game_setup_flow.test.jsx` — covers FR-001 through FR-005 and
  FR-004a end-to-end on the frontend (FR-007)

**Checkpoint**: User Story 1 is fully implemented, tested, and independently verifiable per its
Independent Test criterion above.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T021 [P] Run `quickstart.md`'s 10 backend contract checks and 8 frontend end-to-end checks
  against a local (or dev-deployed) environment; fix any discrepancy found before proceeding
- [ ] T022 Constitution Principle IX (NON-NEGOTIABLE) final acceptance: the requesting user or
  product owner exercises the complete setup flow end-to-end against the real deployed
  environment (or the most representative environment available) and explicitly confirms it
  behaves as intended — not satisfied by any automated test result or by the implementing
  agent's own testing. This task is the last one in this feature and is not complete until that
  confirmation is recorded.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A — skipped, nothing to do.
- **Foundational (Phase 2)**: No dependencies — start immediately. BLOCKS Phase 4's backend
  tasks (T011, T013 need `authorize_player`).
- **UI Design Sign-off (Phase 3)**: No dependencies — can run in parallel with Phase 2. BLOCKS
  Phase 4's frontend tasks (T014–T020) specifically; does not block Phase 4's backend tasks.
- **User Story 1 (Phase 4)**: Backend tasks depend on Phase 2; frontend tasks depend on Phase 3
  AND on Phase 4's backend tasks being far enough along that `gameService.js` (T014) has real
  endpoints to call (T011, T013).
- **Polish (Phase 5)**: Depends on Phase 4 being complete.

### Within Phase 4

- Tests (T005–T009) MUST be written first and MUST fail before their corresponding
  implementation task
- T010 → T011 → T012 (service method before handler before route registration)
- T013 depends on T002 (uses `authorize_player`)
- T014 depends on T011 and T013 existing (calls their routes) — but can be scaffolded against
  contracts/api.md in parallel and wired up once the backend routes exist
- T015, T016, T017 depend on T014 (`gameService.js`) and on T004 (design sign-off)
- T018 depends on T015, T016, T017
- T019 depends on T015, T016, T017 (tests the components they build)
- T020 depends on T018 (tests the assembled page)

### Parallel Opportunities

- T001 can run while T003/T004 (Phase 3) proceed
- T005, T006, T007, T008, T009 (all Phase 4 tests, different files/functions) can be written in
  parallel
- T014 and T019 are marked [P] relative to their siblings where they touch different files

---

## Parallel Example: Phase 4 Tests

```bash
Task: "Unit test Story-list-to-AdventureSummary filtering in src/backend/tests/unit/test_story_service.py"
Task: "Unit test POST /api/game/start field validation in src/backend/tests/unit/test_game_start_validation.py"
Task: "Integration test GET /api/game/adventures in src/backend/tests/integration/test_game_adventures_endpoint.py"
Task: "Integration test POST /api/game/start in src/backend/tests/integration/test_game_start_endpoint.py"
```

---

## Implementation Strategy

### MVP First (and only) Scope

This feature has a single user story (US1) — there is no smaller MVP slice within it. The
minimum shippable increment is:

1. Phase 2: Foundational (`authorize_player`)
2. Phase 3: UI design sign-off (Principle XI gate)
3. Phase 4: User Story 1, backend then frontend
4. Phase 5: Polish — quickstart validation, then the Principle IX user-verified acceptance task

### Incremental Delivery

Backend (T001–T013) can be built and merged ahead of frontend work, since it is independently
testable via the integration tests (T007–T009) without any UI. Frontend work (T014–T020) is
gated on the design sign-off (T004) regardless of backend progress.
