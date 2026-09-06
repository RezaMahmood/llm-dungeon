---

description: "Task list for 009-save-and-continue"
---

# Tasks: Save and Continue

**Input**: Design documents from `/specs/009-save-and-continue/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks ARE included and are not optional here — Constitution Principle I
(Meaningful, Automated Testing) is NON-NEGOTIABLE, and spec FR-007 names the specific
persistence outcomes that each require a corresponding automated test.

**Execution model**: **Strictly sequential across phases and across the two user stories.**
The two stories share eight files, so they are *not* safe to build concurrently — see
[Sequencing](#sequencing--dependencies) for the authoritative order. Parallelism exists only
inside the `[P]` groups called out there.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel **with the other `[P]` tasks in the same group** (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths are included in every task

## Path Conventions

Web app split, per plan.md: `src/backend/` (Python, Azure Functions) and `src/frontend/`
(React). Backend tests live in `src/backend/tests/{unit,integration}/`; frontend tests in
`src/frontend/tests/`.

**Canonical screen name**: the **stories screen** is the route `/game` — it lists the
player's in-progress games (this feature) above the adventures they can start
(`006-adventure-and-character-setup`). `/menu` is the capability chooser, not the stories
screen, despite the nav bar labelling its link "My stories" (a pre-existing mismatch from
`022-persistent-nav-redesign`, out of scope here).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a green baseline. This phase is deliberately small — this feature
adds **no dependency, no Cosmos container, and no Terraform change** (research.md Decision
1), so there is nothing to scaffold.

- [X] T001 Establish a green baseline: run `pytest` in `src/backend` and `npm test` in `src/frontend`, and record any pre-existing failure so it is not later mistaken for a regression from this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The read path `008-core-gameplay` never built, plus the model change both
stories depend on. US1 cannot list anything and US2 cannot decide whether to prompt on
sign-out until `GET /api/game/sessions` exists.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Write model unit tests in `src/backend/tests/unit/test_models.py`: `CheckpointMarker` to_dict/from_dict round-trip, `PlaySession` round-trip preserving `checkpoints`, and a legacy `PlaySession` document with **no** `checkpoints` key loading as `[]` (data-model.md "Change to `PlaySession`")
- [X] T003 [P] Write listing unit tests in `src/backend/tests/unit/test_play_session_service.py` for `list_player_sessions`: only the caller's own sessions, only `status == "active"`, ordered by `lastInteractionAt` descending, `adventureName` resolved once per distinct `adventureId`, fallback to `"Adventure"` when the story cannot be read, `locationLabel`/`progress`/`turnCount`/`checkpointCount` projected from the latest turn, and **no** `turns` array in any row (data-model.md "Saved Game Summary")
- [X] T004 [P] Write integration tests for `GET /api/game/sessions` in a new `src/backend/tests/integration/test_saved_games_endpoint.py`: 200 with the caller's rows, 200 with `sessions: []` for a player with none (never a 404), another player's sessions absent, concluded sessions absent, and an unauthenticated/non-Player caller rejected by `authorize_player` (contracts/api.md; quickstart Scenarios 1–2; SC-002)
- [X] T005 Add the `CheckpointMarker` dataclass and the `checkpoints: list[CheckpointMarker]` field (default `[]`, absent-key tolerant in `from_dict`) to `src/backend/models/play_session.py`
- [X] T006 Implement `list_player_sessions(player_id)` in `src/backend/services/play_session_service.py` — cross-partition query on `playerId` + `status = 'active'` (same query shape `_deactivate_other_active_sessions` already uses), sorted newest-activity-first, with adventure names batch-resolved through `StoryService.get_story` by distinct `adventureId` (research.md Decision 4)
- [X] T007 Implement the `list_sessions` handler in `src/backend/api/game/sessions.py`, reusing `authorize_player` and returning the `{"status": "success", "sessions": [...]}` shape from contracts/api.md
- [X] T008 Register `GET /api/game/sessions` in `src/backend/function_app.py`, following the existing `game_sessions_*` route pattern
- [X] T009 [P] Add `listSavedGames(token)` to `src/frontend/src/services/gameService.js` and export it from the default export, matching the existing `X-Custom-Authorization` header pattern

**Checkpoint**: The player's in-progress games can be listed from both tiers. **Proceed to US1 — do not start US2 yet** (see Sequencing).

---

## Phase 3: User Story 1 - Player Continues a Saved Game (Priority: P1) 🎯 MVP

**Goal**: A returning player sees their own in-progress games, resumes one, and finds the
full prior narrative restored — including switching between two games without a
confirmation step.

**Independent Test**: With a player holding one previously saved, in-progress game, open
the stories screen (`/game`), confirm only that player's own games are listed, click
Resume, and confirm play continues with the complete prior narrative on screen (quickstart
Scenarios 1, 2, 8).

### Tests for User Story 1 ⚠️

- [X] T010 [P] [US1] Write unit tests for `get_session_for_player` in `src/backend/tests/unit/test_play_session_service.py`: full `turns` returned oldest-first, ownership mismatch raises `ForbiddenError`, missing session raises `SessionNotFoundError`, and a concluded session **is** readable (only the list excludes it)
- [X] T011 [P] [US1] Write integration tests for `GET /api/game/sessions/{sessionId}` in `src/backend/tests/integration/test_saved_games_endpoint.py`: 200 with every turn and the full summary field set for the owner, 403 with the generic access-not-granted body for another player (never a 404 that would confirm the id exists), 404 for an unknown id (contracts/api.md; quickstart Scenario 1 steps 4–5)
- [X] T012 [P] [US1] Write component tests in a new `src/frontend/tests/components/GameSetup/StoriesInProgress.test.jsx`: rows render adventure title, last-played and location, ordering follows the supplied list, the active game is marked with **text as well as styling** (Principle VIII — never colour alone), a row with `checkpointCount > 0` shows its saved indicator, and the empty state renders the "nothing to continue" message rather than an empty box (FR-002)
- [X] T013 [P] [US1] Extend `src/frontend/tests/Play/PlayPage.test.jsx`: a resumed session rendered from `initialTurns` shows every prior turn in order, and the status panel reflects the **latest** turn
- [X] T014 [P] [US1] Write an integration test in a new `src/frontend/tests/integration/save_and_continue.test.jsx` covering list → Resume → play: resuming a row with `isActiveForPlayer: false` calls `POST .../resume` first, resuming a row already `true` calls it **not at all**, and a stale row that returns `409 already_active` is treated as success with no error shown (FR-001a, spec Edge Case 5, research.md Decision 5)

### Implementation for User Story 1

- [X] T015 [US1] Implement `get_session_for_player(session_id, player_id)` in `src/backend/services/play_session_service.py`, raising the existing `SessionNotFoundError`/`ForbiddenError` and returning the full `PlaySession`
- [X] T016 [US1] Implement the `get_session` handler in `src/backend/api/game/sessions.py` returning the `{"status": "success", "session": {...}}` detail shape from contracts/api.md, mapping `ForbiddenError` to `forbidden_access_not_granted()`
- [X] T017 [US1] Register `GET /api/game/sessions/{sessionId}` in `src/backend/function_app.py`
- [X] T018 [P] [US1] Add `getSession(token, sessionId)` to `src/frontend/src/services/gameService.js`
- [X] T019 [P] [US1] Create `src/frontend/src/components/GameSetup/SavedGameRow.jsx` — one row per `02-story-select.html`: ordinal, adventure title, "chapter · last played · location" meta line, progress bars, a saved indicator driven by `checkpointCount`, and the Resume action, using only the vendored design tokens and shared component classes
- [X] T020 [US1] Create `src/frontend/src/components/GameSetup/StoriesInProgress.jsx` — section heading, loading and error states, the empty-state message (FR-002), the active-game marker, and a **visible divider** closing the section (Constitution "Screen contracts → Adventure select")
- [X] T021 [US1] Change `src/frontend/src/pages/PlayPage.jsx` to accept `initialTurns` (an array) in place of `initialNarrative`, seeding its `turns` state from it so a resumed game renders its whole history (FR-006)
- [X] T022 [US1] Wire `src/frontend/src/pages/GamePage.jsx`: fetch `listSavedGames` on mount, render `StoriesInProgress` **above** the "01 — Choose an adventure" section with the divider between them (research.md Decision 9), and on Resume call `POST .../resume` only when the row reports `isActiveForPlayer: false` (treating `409 already_active` as success), then `getSession` and hand off to `PlayPage` with `initialTurns` — updating the existing new-game handoff to pass `initialTurns: [narrative]`

**Checkpoint**: User Story 1 is independently functional and shippable as the MVP. Validate quickstart Scenarios 1, 2, and 8 before starting US2.

---

## Phase 4: User Story 2 - Player Saves Progress and Returns Home (Priority: P2)

**Goal**: A player can explicitly save a labelled checkpoint and return to the stories
screen, and is asked whether to save when signing out with a game in progress — with
progress identical either way, and a failed checkpoint never trapping them.

**Independent Test**: Start a game, take a few actions, save a checkpoint and exit, then
read that game's stored state directly (`GET /api/game/sessions/{id}`) and confirm every
turn is retained and a marker is present; separately, sign out once accepting and once
declining the prompt and confirm the retained turns are identical both times (quickstart
Scenarios 3, 5, 6, 7, 9). This test reads the API directly rather than going through US1's
screen, so it holds even if US1 has not shipped.

### Tests for User Story 2 ⚠️

- [X] T023 [P] [US2] Write unit tests for `record_checkpoint` in `src/backend/tests/unit/test_play_session_service.py`: the marker's `label` comes from the latest turn's `locationLabel` (falling back to `"Your story"`), `turnNumber` and `createdAt` are set, `turns`/`status`/`summary`/`lastInteractionAt` are **unchanged**, a second save with no interaction in between appends a **second** marker at the same `turnNumber` (spec Edge Case 3), a concluded session raises, and an ETag precondition failure retries once from a fresh read then gives up (research.md Decision 8, data-model.md invariants)
- [X] T024 [P] [US2] Write integration tests for `POST /api/game/sessions/{sessionId}/checkpoints` in `src/backend/tests/integration/test_saved_games_endpoint.py`: 201 with the marker body, 403 for another player, 404 for an unknown id, `409 session_concluded` for a finished game, and `503 checkpoint_unavailable` when the write cannot land (contracts/api.md; quickstart Scenarios 3, 7)
- [X] T025 [US2] Write the **resume-never-rewinds** integration test in `src/backend/tests/integration/test_saved_games_endpoint.py` (FR-003a, FR-007, quickstart Scenario 4): record a checkpoint, submit two further interactions, then `GET /api/game/sessions/{sessionId}` and assert every post-checkpoint turn is present, the marker still reports its original `turnNumber`, and nothing was discarded or rewound. **Not `[P]` with T024** — same file
- [X] T026 [P] [US2] Extend `src/frontend/tests/components/TitleBar.test.jsx`: the "Save a checkpoint" button invokes an `onSaveCheckpoint` supplied via `PlayTitleContext`, mirroring how `onPauseExit` already falls back to the published value, and the button is inert/absent when nothing is published (so the stories screen's title bar offers no dead control)
- [X] T027 [P] [US2] Extend `src/frontend/tests/Play/PlayPage.test.jsx`: a successful save renders a `role="status"` confirmation naming the location that auto-dismisses after ~4 seconds ("visibly and briefly", Constitution "Save and session behaviour" #2), a failed save renders the "couldn't record that checkpoint, but your progress is safe" notice and leaves the game playable, and "Save and exit to my stories" still exits when the save fails (FR-003, FR-006a)
- [X] T028 [P] [US2] Write component tests in a new `src/frontend/tests/components/LogoutSavePrompt.test.jsx`: the prompt states that progress is already safe (FR-004), accepting records a checkpoint then signs out, declining signs out with no checkpoint call, cancelling does neither, a failed checkpoint still completes the sign-out with the failure notice rendered (FR-006a), and the dialog is keyboard-operable with a visible focus indicator
- [X] T029 [P] [US2] Extend `src/frontend/tests/components/NavBar.test.jsx`: signing out shows the prompt only when `listSavedGames` returns a session with `status: "active"` **and** `isActiveForPlayer: true`; sign-out proceeds directly with no prompt when the player has no sessions, when their only game has concluded (so it never appears in the list — spec Edge Case 2), when no returned session is active for them, and when the lookup itself fails (FR-004, spec US2 Acceptance Scenario 5, research.md Decision 6)
- [X] T030 [P] [US2] Extend `src/frontend/tests/integration/save_and_continue.test.jsx` with the sign-out round trip: accepting the prompt records a marker and the resumed game later shows every turn plus the marker; declining records none and the resumed game shows **exactly the same turns** (spec US2 Acceptance Scenarios 3–4; quickstart Scenarios 5–6)

### Implementation for User Story 2

- [X] T031 [US2] Implement `record_checkpoint(session_id, player_id)` in `src/backend/services/play_session_service.py`: ownership check, concluded rejection, label generated from the latest turn, append to `checkpoints`, write with `MatchConditions.IfNotModified` and one retry from a fresh read (research.md Decision 8)
- [X] T032 [US2] Implement the `create_checkpoint` handler in `src/backend/api/game/sessions.py` returning 201 with the marker, `409 session_concluded`, and `503 checkpoint_unavailable` per contracts/api.md — ignoring any client-supplied label
- [X] T033 [US2] Register `POST /api/game/sessions/{sessionId}/checkpoints` in `src/backend/function_app.py`
- [X] T034 [P] [US2] Add `saveCheckpoint(token, sessionId)` to `src/frontend/src/services/gameService.js`
- [X] T035 [P] [US2] Extend `src/frontend/src/context/PlayTitleContext.jsx` so `usePublishPlayTitle` carries `onSaveCheckpoint` alongside `storyTitle`/`onPauseExit` (keeping the referential-stability contract its doc comment already states)
- [X] T036 [US2] Extend `src/frontend/src/components/Layout/TitleBar.jsx` so `onSaveCheckpoint` falls back to the published context value exactly as `onPauseExit` does, and the button is hidden or inert when neither is supplied
- [X] T037 [US2] Extend `src/frontend/src/pages/PlayPage.jsx` to publish a `useCallback`-stable `onSaveCheckpoint` that calls `saveCheckpoint`, renders the auto-dismissing `role="status"` confirmation on success and the non-blocking failure notice on error
- [X] T038 [US2] Make `PauseDialog`'s "Save and exit to my stories" record a checkpoint before calling `onExit` in `src/frontend/src/pages/PlayPage.jsx`, completing the exit **even when the save fails** — no confirm step, no retry gate (FR-003, FR-006a)
- [X] T039 [P] [US2] Create `src/frontend/src/components/Layout/LogoutSavePrompt.jsx` — a `dialog`/`dialog-backdrop` modal matching `PauseDialog`'s pattern, stating that progress is already safe, with save / don't-save / cancel actions, and rendering the failure notice inline without requiring acknowledgement (FR-004, FR-005, FR-006a)
- [X] T040 [US2] Route `NavBar`'s sign-out in `src/frontend/src/components/Layout/NavBar.jsx` through `LogoutSavePrompt`: call `listSavedGames` first and prompt only when a session is `status: "active"` and `isActiveForPlayer: true`, otherwise call `instance.logoutRedirect()` directly; a failed lookup must fall through to a plain sign-out rather than blocking it

**Checkpoint**: Both user stories are complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T041 [P] Accessibility pass over the three new surfaces (`StoriesInProgress`, `SavedGameRow`, `LogoutSavePrompt`): keyboard operability with a visible focus indicator, real buttons over clickable divs, 4.5:1 body-copy contrast, and no meaning carried by colour alone (Constitution "Accessibility")
- [X] T042 [P] Confirm the new surfaces use only the vendored design-token layer and shared component classes — no ad hoc colours or spacing — and that the play surface gained **no** new chrome beyond the already-designed "Save a checkpoint" button (Principle VIII, FR-016 of `008-core-gameplay`)
- [X] T043 [P] Update `specs/designs/README.md` so `02-story-select.html`'s "stories in progress" section maps to `009-save-and-continue` and `03-play.html`'s checkpoint-save action maps to this feature's FR-003
- [X] T044 Verify no `infrastructure/terraform/` change is needed and no new Cosmos container was introduced, and that a `PlaySession` document written before this feature still loads (research.md Decision 1, data-model.md)
- [X] T045 Run the full backend and frontend suites (`pytest` in `src/backend`, `npm test` in `src/frontend`) and confirm no regression against the T001 baseline
- [ ] T046 Walk [quickstart.md](./quickstart.md) Scenarios 1–9 against the local stack and confirm each expectation, including the failure path in Scenario 9
- [ ] T047 Playtest the continue and save flows against the deployed environment and file any findings as follow-up work — informational only, non-blocking per Constitution Principle IX

---

## Sequencing & Dependencies

### Authoritative execution order

Work proceeds strictly top to bottom. Tasks on the same numbered line may run
concurrently; everything else is sequential.

| Step | Tasks | Notes |
|------|-------|-------|
| 1 | T001 | Baseline must be green (or its failures recorded) before anything changes |
| 2 | T002, T003, T004 **and** T009 | Four different files. T009 is frontend-only and independent of the backend work below |
| 3 | T005 | `models/play_session.py` — T002 asserts it |
| 4 | T006 | `play_session_service.py` — needs T005's model |
| 5 | T007 | `api/game/sessions.py` — needs T006 |
| 6 | T008 | `function_app.py` — needs T007 |
| — | **Phase 2 checkpoint** | The list endpoint works end to end |
| 7 | T010, T011, T012, T013, T014 | Five different test files |
| 8 | T015 | `play_session_service.py` |
| 9 | T016 | `api/game/sessions.py` |
| 10 | T017 | `function_app.py` |
| 11 | T018, T019 | `gameService.js` and `SavedGameRow.jsx` |
| 12 | T020 | `StoriesInProgress.jsx` — needs T019 |
| 13 | T021 | `PlayPage.jsx` |
| 14 | T022 | `GamePage.jsx` — needs T018, T020, T021 |
| — | **US1 checkpoint / MVP** | Validate quickstart Scenarios 1, 2, 8 and stop here if shipping the MVP |
| 15 | T023, T024, T026, T027, T028, T029, T030 | Seven different test files |
| 16 | T025 | Same file as T024, so it follows it |
| 17 | T031 | `play_session_service.py` |
| 18 | T032 | `api/game/sessions.py` |
| 19 | T033 | `function_app.py` |
| 20 | T034, T035, T039 | `gameService.js`, `PlayTitleContext.jsx`, `LogoutSavePrompt.jsx` |
| 21 | T036 | `TitleBar.jsx` — needs T035 |
| 22 | T037 | `PlayPage.jsx` — needs T034, T035 |
| 23 | T038 | `PlayPage.jsx` again — follows T037 |
| 24 | T040 | `NavBar.jsx` — needs T034, T039 |
| — | **US2 checkpoint** | Validate quickstart Scenarios 3, 5, 6, 7, 9 |
| 25 | T041, T042, T043 | Three different concerns/files |
| 26 | T044 | |
| 27 | T045 | Full suites vs. the T001 baseline |
| 28 | T046 | Quickstart walk-through |
| 29 | T047 | Playtest — informational, does not gate completion (Principle IX) |

### Why the two stories are sequential, not parallel

US1 and US2 have no *logical* dependency — US2's endpoints and prompt work whether or not
the continue screen exists, and its Independent Test reads the API directly rather than
going through US1's screen. But they modify **eight of the same files**, so building them
concurrently means eight merge conflicts, not a speed-up:

| File | US1 task | US2 task |
|------|----------|----------|
| `src/backend/services/play_session_service.py` | T015 | T031 |
| `src/backend/api/game/sessions.py` | T016 | T032 |
| `src/backend/function_app.py` | T017 | T033 |
| `src/backend/tests/unit/test_play_session_service.py` | T010 | T023 |
| `src/backend/tests/integration/test_saved_games_endpoint.py` | T011 | T024, T025 |
| `src/frontend/src/services/gameService.js` | T018 | T034 |
| `src/frontend/tests/Play/PlayPage.test.jsx` | T013 | T027 |
| `src/frontend/tests/integration/save_and_continue.test.jsx` | T014 | T030 |

US1 ships first because it is the higher-priority story (P1), is the MVP on its own, and
closes the gap that makes resuming impossible today.

### Within each phase

- Test tasks are written first and must fail before the implementation tasks in the same phase
- Models → services → endpoints → routes → client → components → page wiring

---

## Implementation Strategy

### MVP first (Steps 1–14: T001–T022)

1. Phase 1 Setup (T001)
2. Phase 2 Foundational (T002–T009) — **blocks everything**
3. Phase 3 User Story 1 (T010–T022)
4. **STOP and VALIDATE**: quickstart Scenarios 1, 2, and 8 — a player can continue a saved
   game across visits, which is the whole reason persistence exists
5. Deploy/demo if ready

This is a genuine MVP on its own: it closes the gap where `008` could persist a session but
never read one back.

### Incremental delivery

1. Setup + Foundational → the read path exists
2. Add US1 → continue a saved game → deploy/demo (**MVP**)
3. Add US2 → explicit checkpoints and the sign-out prompt → deploy/demo
4. Polish → accessibility, design-system, README, and full quickstart validation

---

## Notes

- `008-core-gameplay`'s three existing endpoints are **not modified** by any task here,
  including `POST .../resume`'s `409 already_active` — T014/T022 handle that client-side
  (research.md Decision 5)
- No task touches `infrastructure/terraform/`; checkpoint markers are embedded on the
  existing `playSessions` documents
- Nothing in this feature calls the LLM, so no task adds prompt files, token accounting, or
  AI cost telemetry
- The sign-out control exists only in `NavBar`, which is absent from the play surface and
  from `/game`; the prompt therefore fires from `/menu` and the admin screens, gated on the
  server's own active-game flag (research.md Decision 6, spec Assumptions)
- Commit after each task or logical group; stop at either story checkpoint to validate
  independently
