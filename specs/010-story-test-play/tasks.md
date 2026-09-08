---

description: "Task list for 010-story-test-play"
---

# Tasks: Story Test Play

**Input**: Design documents from `/specs/010-story-test-play/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Included. FR-012 requires an automated test for each of six named outcomes, and Principle I is non-negotiable.

**Organization**: The spec has one user story (US1, P1), so Phase 3 carries the feature and is grouped by layer with checkpoints.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — **different file** from every other `[P]` task in the same phase, no dependency on an incomplete task
- **[Story]**: Which user story this task belongs to
- Exact file paths are given in every task

## Path Conventions

Web application per plan.md: `src/backend/` (Azure Functions, Python 3.11) and `src/frontend/` (React 19 SPA). Backend tests in `src/backend/tests/{unit,integration}/`; frontend tests in `src/frontend/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Provision the `testPlaySessions` container across config, local seeding, and infrastructure

**Blocks**: T018 only. Phase 2 does not depend on this phase and may run alongside it.

- [ ] T001 [P] Add `TEST_PLAY_SESSIONS_CONTAINER = "testPlaySessions"` to the `Config` class in `src/backend/config.py`, alongside the existing container constants
- [ ] T002 [P] Add `"testPlaySessions": "/id"` to `CONTAINER_PARTITION_KEY_PATHS` in `src/backend/db/seed_data.py` so `ensure_containers()` creates it for local runs
- [ ] T003 [P] Add an `azurerm_cosmosdb_sql_container` resource named `test_play_sessions` (`name = "testPlaySessions"`, `partition_key_paths = ["/id"]`, `partition_key_version = 2`) in `infrastructure/terraform/main.tf`, mirroring the existing `play_sessions` resource

**Checkpoint**: The container exists locally and in infrastructure; no behavior depends on it yet

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The model, the shared completion rules, and the `Story.lastTestPlayedAt` writer — the missing half of the already-merged publish gate

**⚠️ CRITICAL**: Phase 3 cannot begin until this phase is complete. This phase has no dependency on Phase 1.

- [ ] T004 [P] Create `TestPlaySession` and `TestPlayExchange` dataclasses with `to_dict()`/`from_dict()` in `src/backend/models/test_play_session.py`, per the field tables in `specs/010-story-test-play/data-model.md` (note: `storyId`/`administratorId`, no `checkpoints`, no `isActiveForPlayer`)
- [ ] T005 [P] Create `src/backend/services/completion_rules.py` containing module-level `evaluate_completion(story, session, turn_data)` and `rule_satisfied(configured, satisfied_indices, rule)`, reproducing the current logic of `PlaySessionService._evaluate_completion`/`_rule_satisfied` (success checked before failure; reads the `newlySatisfiedSuccessConditions`/`newlySatisfiedFailureConditions` index lists). **Creates a new file only — does not edit `play_session_service.py`.**
- [ ] T006 Delete the now-duplicated `_evaluate_completion` and `_rule_satisfied` methods from `src/backend/services/play_session_service.py` and delegate to `completion_rules` from T005, leaving real-play behavior byte-for-byte identical (depends on T005)
- [ ] T007 [P] Add `record_test_play(story_id)` to `StoryService` in `src/backend/services/story_service.py`, stamping `lastTestPlayedAt = _now()` and upserting — it MUST NOT touch `contentUpdatedAt`, `published`, or `lastPublishedAt`
- [ ] T008 [P] Add unit tests for the shared completion rules in `src/backend/tests/unit/test_completion_rules.py`, covering `any`/`all` rules, the success-before-failure tie, and the no-newly-satisfied-conditions case
- [ ] T009 [P] Add unit tests for `record_test_play` in `src/backend/tests/unit/test_story_service.py`, asserting `lastTestPlayedAt` is set, `contentUpdatedAt` is unchanged, and `can_publish()` flips from `False` to `True`

**Checkpoint**: Existing gameplay tests still pass after T006; `can_publish()` is satisfiable for the first time

---

## Phase 3: User Story 1 - Administrator Test-Plays a Draft Story Before Publishing (Priority: P1) 🎯 MVP

**Goal**: An administrator runs an interactive test session against a draft story, aborts it with a warning, or reaches an ending and publishes (confirmed) or returns to the wizard.

**Independent Test**: With one draft story that has a saved world prompt, character types, and completion criteria, start a test-play session, submit instructions, verify narrative responses follow that configuration, and verify the story becomes publishable only after an exchange.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST and ensure they FAIL before implementation.**
> T010–T013 all write `src/backend/tests/unit/test_test_play_session_service.py`, so they run **sequentially with respect to each other**. Only T010 carries `[P]`, marking that the group as a whole runs parallel to T014–T017.

- [ ] T010 [P] [US1] Backend service tests for session creation and exchanges in `src/backend/tests/unit/test_test_play_session_service.py` — FR-001, FR-002; asserts a draft (`published=False`) story is testable and that turn 0 does **not** stamp `lastTestPlayedAt`
- [ ] T011 [US1] Backend service tests for completion-criteria triggering in `src/backend/tests/unit/test_test_play_session_service.py` — FR-004, FR-006; stubbed LLM returns `newlySatisfiedSuccessConditions: [0]`, asserts `status == "concluded"` and the `completionReason` payload (same file as T010)
- [ ] T012 [US1] Backend service tests for abort/delete in `src/backend/tests/unit/test_test_play_session_service.py` — FR-005, FR-010; asserts the session document is gone and `Story.lastTestPlayedAt` survives the delete (same file as T010)
- [ ] T013 [US1] Backend isolation tests in `src/backend/tests/unit/test_test_play_session_service.py` — FR-009; a second administrator's session id is rejected, two administrators testing the **same story concurrently** each get an independent session, and no write reaches `playSessions` or `playerContentSafetyStandings` (same file as T010)
- [ ] T014 [P] [US1] Backend endpoint tests in `src/backend/tests/integration/test_admin_test_play_endpoint.py` — all four routes from `contracts/api.md`: status codes, `authorize_admin` enforcement, the full error table, and that a successful exchange stamps `lastTestPlayedAt`
- [ ] T015 [P] [US1] Test-play screen tests in `src/frontend/tests/components/AdminStoryTestPlayPage.test.jsx` — FR-003 (test/draft marking conveyed as text), FR-005 (**restart warning dismissed** leaves the conversation intact; **restart confirmed** deletes the session and navigates to `/admin/stories/:storyId/edit`)
- [ ] T016 [P] [US1] Conclusion-flow integration tests in `src/frontend/tests/integration/admin_test_play_flow.test.jsx` — FR-006, FR-007 (**publish from conclusion**: confirm, then navigate to `/admin`), FR-008 (**edit from conclusion**: return to the wizard), and the blocked-publish edge case that stays on the conclusion screen
- [ ] T017 [P] [US1] Extend `src/frontend/tests/components/StoryPublishActions.test.jsx` and `src/frontend/tests/components/StoryWizard/StepPublish.test.jsx` for the amended `005` FR-013 publish confirmation, asserting no publish request is sent until the dialog is confirmed (owns both files; no other task touches them)

### Backend implementation for User Story 1

- [ ] T018 [US1] Implement `TestPlaySessionService.create_session(story_id, administrator_id)` in `src/backend/services/test_play_session_service.py` — reads the story with **no `published` check**, defaults the character to `story.characterTypes[0]` with name `"Tester"`, generates turn 0 via `LLMService.generate_gameplay_turn(story, session, None)`, and persists to `config.TEST_PLAY_SESSIONS_CONTAINER` (depends on T001, T004)
- [ ] T019 [US1] Implement `TestPlaySessionService.submit_exchange(session_id, administrator_id, raw_input)` in `src/backend/services/test_play_session_service.py` — rejects empty/whitespace input, enforces the 2-second interval and the `_etag`/`MatchConditions.IfNotModified` single-flight claim, generates the turn, evaluates completion via `completion_rules.evaluate_completion`, and concludes the session when it returns non-`None`
- [ ] T020 [US1] Inside the `submit_exchange` method written in T019 (`src/backend/services/test_play_session_service.py`), call `StoryService.record_test_play(story_id)` after a turn with `playerInput is not None` has persisted successfully — it must live in the service method, **not** in the route handler, so every caller stamps the marker. Never on turn 0, never on session creation (research Decision 9)
- [ ] T021 [US1] Handle `LLMContentFilteredError` in `src/backend/services/test_play_session_service.py` by returning the in-fiction deflection turn **without** calling `PlayerContentSafetyStandingService.record_flag` and without any lockout check (research Decision 4); map `LLMOutputError`/`LLMRateLimitError` to a narrative-unavailable error
- [ ] T022 [US1] Implement `delete_session(session_id, administrator_id)` and `get_session(session_id, administrator_id)` in `src/backend/services/test_play_session_service.py` — both reject another administrator's session; delete is idempotent per document and never clears `Story.lastTestPlayedAt`
- [ ] T023 [US1] Implement the four route handlers in `src/backend/api/admin/test_play.py` per `contracts/api.md`, each starting with `authorize_admin(req)` and emitting the `_narrative_dict` shape (`turnNumber`, `narrativeText`, `suggestedActions`, `locationLabel`, `goalLabel`, `progress`) (depends on T018–T022)
- [ ] T024 [US1] Register the four routes in `src/backend/function_app.py` wrapped in `_guarded(...)`: `POST manage/stories/{storyId}/test-play`, `POST manage/test-play-sessions/{sessionId}/interactions`, `DELETE manage/test-play-sessions/{sessionId}`, `GET manage/test-play-sessions/{sessionId}` (depends on T023)

**Checkpoint**: T010–T014 pass. A draft story is test-playable and publishable through the API with no UI.

### Frontend implementation for User Story 1

- [ ] T025 [P] [US1] Create `src/frontend/src/services/testPlayService.js` with `startTestPlay`, `submitTestPlayInstruction`, `deleteTestPlaySession`, and `getTestPlaySession`, following the existing `axios.create({ baseURL: "/api" })` + `X-Custom-Authorization` pattern
- [ ] T026 [US1] Add publish-confirmation state (`confirmingPublish`, `requestPublish`, `confirmPublish`, `cancelPublish`) and an optional `onPublished` callback to `src/frontend/src/hooks/usePublishToggle.js`, mirroring the existing unpublish trio and leaving `gateMessage` unchanged
- [ ] T027 [US1] Add the publish-confirmation dialog and the optional `onPublished` prop to `src/frontend/src/components/Admin/StoryPublishActions.jsx`, reusing the existing inline `.dialog-backdrop`/`.dialog`/`.dialog-title`/`.dialog-body`/`.dialog-actions` markup with `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` — this satisfies amended `005` FR-013 at the story-list and wizard entry points at once (depends on T026)
- [ ] T028 [US1] Create `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` — loads the story, starts a session via T025, and renders the conversation by reusing `StoryPane`, `InstructionInput`, `SuggestedActions`, and `StatusPanel` from `src/frontend/src/components/Play/`; marks the session as test/draft in text, not color alone (FR-003)
- [ ] T029 [US1] Add the restart/abort warning dialog to `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` (FR-005) — shown **before anything happens**, stating the session will be aborted and deleted; dismiss leaves session state untouched, confirm calls `deleteTestPlaySession` then navigates to `/admin/stories/:storyId/edit` (depends on T028)
- [ ] T030 [US1] Add the conclusion screen to `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` (FR-006) — rendered when a response returns `status: "concluded"`, stating the playthrough concluded and offering the publish and edit actions (depends on T028)
- [ ] T031 [US1] Wire the conclusion screen's publish action in `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` by rendering `StoryPublishActions` with `onPublished` navigating to `/admin` (FR-007) — never a separate publish path; a blocked or failed publish keeps the administrator on the conclusion screen showing `gateMessage` (depends on T027, T030)
- [ ] T032 [US1] Wire the conclusion screen's edit action in `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` to navigate to `/admin/stories/:storyId/edit` (FR-008) (depends on T030)
- [ ] T033 [US1] Register the lazy-loaded route `/admin/stories/:storyId/test-play` → `AdminStoryTestPlayPage` inside `<ProtectedRoute capability="Administrator">` in `src/frontend/src/App.jsx` (depends on T028)
- [ ] T034 [US1] Add the test-play entry point to the wizard's terminal screen in `src/frontend/src/pages/AdminStoryWizardPage.jsx` — a link to `/admin/stories/${story.id}/test-play`, rendered where `story` is set, alongside the existing `Publish & assign` section (depends on T033)

**Checkpoint**: User Story 1 is fully functional and independently testable end to end

---

## Phase 4: Polish & Cross-Cutting Concerns

- [ ] T035 Verify the FR-011 accessibility bar on `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` — keyboard-only operation end to end, visible `:focus-visible` focus, a real `<label>` on the instruction input, `aria-live="polite"` on the narrative region, and both dialogs carrying `role="dialog"`/`aria-modal`/`aria-labelledby`
- [ ] T036 Confirm no off-system styling in `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` by grepping for hex literals, bare `font-family`, and raw pixel values that a design token in `src/frontend/src/styles/designTokens.css` already covers
- [ ] T037 Run `pytest src/backend/tests/ -v` and, from `src/frontend/`, `npm test` — confirm the pre-existing suites `src/backend/tests/unit/test_play_session_service.py` and `src/frontend/tests/integration/admin_story_publish_flow.test.jsx` still pass after the T006 refactor and the T027 confirmation change
- [ ] T038 Walk the five validation scenarios in `specs/010-story-test-play/quickstart.md`, especially Scenario 1 (publishable only after an exchange) and Scenario 4 (isolation)
- [ ] T039 Verify the step-05 notes already recorded in `specs/designs/README.md` (flagging unimplemented, restart aborts to the edit page, deferred visual design) match what shipped, and correct them only if implementation diverged

---

## Requirement → Task Traceability

Every functional requirement and acceptance scenario maps to at least one test task and one implementation task.

| Requirement | Test task(s) | Implementation task(s) |
|---|---|---|
| FR-001 start a session against saved config | T010, T014 | T018, T023, T024 |
| FR-002 same generation + safety screening | T010, T014 | T018, T019, T021 |
| FR-003 visibly distinguished from real play | T015 | T028 |
| FR-004 completion criteria enforced | T008, T011 | T005, T019 |
| FR-005 restart warns, then aborts and deletes | T012, T015 | T022, T029 |
| FR-006 conclusion announced, offers both actions | T011, T016 | T030 |
| FR-007 publish confirmed, then to story list | T016, T017 | T026, T027, T031 |
| FR-008 edit returns to the wizard | T016 | T032 |
| FR-009 isolation from other sessions | T013, T014 | T001–T003, T018, T022 |
| FR-010 delete does not reset test-play status | T009, T012 | T007, T020, T022 |
| FR-011 design deferred, accessibility intact | T015 | T028, T035, T036 |
| FR-012 automated test per outcome | T010–T017 | — |
| Amended `005` FR-013 publish confirms | T017 | T026, T027 |

| Acceptance scenario (US1) | Task(s) |
|---|---|
| 1 — responses use the story's configuration | T010, T018 |
| 2 — response marked as test/draft | T015, T028 |
| 3 — criteria conclude the session | T011, T019, T030 |
| 4 — publish confirmed → story list | T016, T031 |
| 5 — edit → wizard with story loaded | T016, T032 |
| 6 — restart warns, then aborts to edit page | T012, T015, T029 |

| Edge case | Task(s) |
|---|---|
| Two administrators, same story, concurrently | T013 |
| Restart warning dismissed | T015, T029 |
| Publish blocked or fails at conclusion | T016, T031 |

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. Blocks T018 only
- **Foundational (Phase 2)**: No dependency on Phase 1 — may run alongside it. BLOCKS all of Phase 3
- **User Story 1 (Phase 3)**: Depends on Phase 2 complete, and on T001 before T018
- **Polish (Phase 4)**: Depends on Phase 3

### Within User Story 1

- Tests T010–T017 are written first and must fail before implementation
- T005 → T006 (create the module, then remove the duplicate)
- T018–T022 → T023 → T024 (service, then handlers, then registration)
- T020 depends on T007 and T019
- T026 → T027 → T031 (hook state, then dialog, then reuse on the conclusion screen)
- T028 → T029, T030, T033; T030 → T031, T032; T033 → T034

### Parallel Opportunities

- Phase 1: T001, T002, T003 — three separate files
- Phase 2: T004, T005, T007, T008, T009 — separate files. T006 waits on T005
- Phase 3 tests: the T010–T013 group (one file, internally sequential) runs parallel to T014, T015, T016, T017
- T025 runs parallel to all backend work (T018–T024)
- Phase 4: T035 and T036 both only *read* `AdminStoryTestPlayPage.jsx`, so they may run together; T037 and T038 are sequential gates

---

## Parallel Example: User Story 1 tests

```bash
# Four independent units, launched together.
# The first is a single sequential unit (T010 -> T011 -> T012 -> T013, one shared file):
Task: "Backend service tests in src/backend/tests/unit/test_test_play_session_service.py"        # T010-T013
Task: "Backend endpoint tests in src/backend/tests/integration/test_admin_test_play_endpoint.py" # T014
Task: "Test-play screen tests in src/frontend/tests/components/AdminStoryTestPlayPage.test.jsx"  # T015
Task: "Conclusion flow tests in src/frontend/tests/integration/admin_test_play_flow.test.jsx"    # T016
```

---

## Implementation Strategy

### MVP (User Story 1 is the whole feature)

1. Phase 1 + Phase 2 in parallel — independent of each other
2. Phase 2 is **the highest-value increment**: once T007 lands, `can_publish()` is satisfiable and the standing "no story can be published at all" condition becomes fixable
3. Phase 3 backend (T018–T024) — independently verifiable via T014 before any UI exists
4. **STOP and VALIDATE**: quickstart.md Scenario 1
5. Phase 3 frontend (T025–T034), then Phase 4

### Incremental Delivery

- Phases 1–2 → the gate's missing writer exists and is unit-tested
- Phase 3 backend → a draft story is test-playable and publishable via the API
- Phase 3 frontend → the administrator-facing flow is complete
- Phase 4 → accessibility and full-suite validation

---

## Notes

- `017-story-publish-test-play-gate`'s FR-001/FR-002/FR-003 code is already merged; no task re-implements the gate. T007 supplies the writer it reads
- The publish confirmation (T026–T027) reaches all three entry points because the story list and `StepPublish` already render `StoryPublishActions`
- FR-011 defers visual design only — T035 is not optional
- A saved `Story` always has at least one success condition (`CompletionCriteria.__post_init__` in `src/backend/models/story.py`), so every test-play session has a reachable ending. The spec's unreachable "no completion criteria" edge case was dropped on 2026-09-08
- T006 modifies merged `008-core-gameplay-done` code; T037 re-runs the existing suites specifically to catch a regression there
- Commit after each task or logical group; stop at any checkpoint to validate
