---

description: "Task list for Story and Session Token Usage Tracking (026-token-usage)"
---

# Tasks: Story and Session Token Usage Tracking

**Input**: Design documents from `/specs/026-token-usage/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Not explicitly requested as TDD, but this project's constitution (Principle I,
NON-NEGOTIABLE) requires meaningful automated coverage for every change, and plan.md's
Project Structure already names the exact test files each change touches — so test tasks
are included alongside each implementation task rather than treated as optional.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent
implementation and testing. Phases run in **priority order** (P1, then the two P2 stories
in spec.md's listed order, then P3) rather than spec.md's narrative order, because User
Story 4's gameplay-turn token capture is the one piece User Story 3's test-play acceptance
scenario also depends on (research.md Decision 3) — sequencing US4 first resolves that
dependency instead of splitting one code path across two out-of-order phases. See
Dependencies & Execution Order below.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Every task names an exact file path

---

## Phase 1: Setup

**Purpose**: The one project-wide, code-independent prerequisite this feature carries —
everything else reuses the existing stack, containers, and dependencies unchanged
(plan.md Technical Context: "No new dependencies").

- [X] T001 Amend `.specify/memory/constitution.md`'s Screen contracts section to add the
  **Administrator — sessions** entry (no prototype screen) exactly as drafted in plan.md's
  "Constitution amendment" section, and bump the constitution's version per its own
  Governance/versioning rule (MINOR — new contract entry) (research.md Decision 9)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared data shapes and the one LLM-call-site signature change every user
story's accumulation logic builds on. No user story's backend work can start until this
phase is complete — every downstream task unpacks a `(payload, tokens_used)` tuple this
phase introduces.

**⚠️ CRITICAL**: Completing this phase alone leaves existing callers of `LLMService`
temporarily unpacking a tuple incorrectly; do not consider the app deployable again until
at least one user story phase (which fixes its owned call sites) is also complete.

- [X] T002 [P] Add `totalTokens: int = 0` to `Story` in `src/backend/models/story.py`,
  including `to_dict`/`from_dict` (data-model.md → Story)
- [X] T003 [P] Add `totalTokens: int = 0` to `StoryDraft` in
  `src/backend/models/story_draft.py`, including `to_dict`/`from_dict` (data-model.md →
  StoryDraft)
- [X] T004 [P] Add `totalTokens: int = 0` to `PlaySession` and `tokens: int = 0` to
  `PlayerInteraction` in `src/backend/models/play_session.py`, including both classes'
  `to_dict`/`from_dict` (data-model.md → PlaySession)
- [X] T005 [P] Add `totalTokens: int = 0` to `TestPlaySession` and `tokens: int = 0` to
  `TestPlayExchange` in `src/backend/models/test_play_session.py`, including both classes'
  `to_dict`/`from_dict` (data-model.md → TestPlaySession)
- [X] T006 [P] Add `"totalTokens"` to `SYSTEM_MANAGED_KEYS` in
  `src/backend/services/story_config_file.py` so it never round-trips through Story
  Configuration File export/import (data-model.md → Story, "Excluded from the Story
  Configuration File")
- [X] T007 Change `LLMService._call()` and every public generation method
  (`suggest_world_prompt`, `generate_story_config`, `generate_starting_point`,
  `generate_gameplay_turn`, `summarize_session_history`) in
  `src/backend/services/llm_service.py` to each return a `(payload, tokens_used)` pair,
  where `tokens_used = input_tokens + output_tokens` read from the same usage data the
  existing OpenTelemetry span already computes (research.md Decision 1)
- [X] T008 Update `src/backend/tests/unit/test_llm_service.py` so every public method's
  assertions match its new `(payload, tokens)` return shape

**Checkpoint**: Foundation ready — model fields exist and `LLMService` hands back token
counts. User story phases can now update their owned call sites to consume them.

---

## Phase 3: User Story 1 - See cumulative token usage for each story (Priority: P1) 🎯 MVP

**Goal**: The admin stories list shows each story's cumulative token total, accurate for
the story's initial creation flow (draft world-prompt suggestions, generation, starting
point).

**Independent Test**: Create a new story through the admin wizard; open the stories list
and confirm its row shows a positive token number matching the sum of the world-prompt
suggestion, `generate_story_config`, and `generate_starting_point` calls made while
creating it (quickstart.md Scenario 1).

### Implementation for User Story 1

- [X] T009 [US1] In `src/backend/services/story_draft_service.py`, update
  `_apply_world_prompt_suggestion` to unpack `(world_prompt, tokens)` from
  `self._llm.suggest_world_prompt(...)` and add `tokens` to `draft.totalTokens` before the
  draft is persisted (data-model.md → StoryDraft lifecycle)
- [X] T010 [US1] In `src/backend/services/story_draft_service.py`, update `generate_story`
  to unpack tokens from the `generate_story_config` and `generate_starting_point` calls and
  pass the draft's accumulated `totalTokens` plus both calls' tokens through to
  `StoryService.create_story` (research.md Decision 2, creation case)
- [X] T011 [US1] In `src/backend/services/story_service.py`, change `create_story` to
  `create_story(self, draft, narrative_guidance, starting_point, tokens_used: int)` and set
  the new `Story.totalTokens = tokens_used`
- [X] T012 [US1] In `src/backend/services/story_service.py`, update `list_summaries()`'s
  Cosmos projection query to also select `c.totalTokens`, defaulting to `0` for a
  pre-existing row missing the field (FR-004)
- [X] T013 [US1] [P] Update `src/backend/tests/unit/test_story_draft_service.py` for the
  draft's `totalTokens` accumulation on `suggest_world_prompt`/`_apply_world_prompt_suggestion`
  and its folding into the newly created `Story.totalTokens` on `generate_story`
- [X] T014 [US1] [P] Update `src/backend/tests/unit/test_story_service.py` for
  `create_story`'s `totalTokens` assignment and `list_summaries`' projection, including a
  legacy-row-with-no-field case defaulting to `0`
- [X] T015 [US1] [P] Update `src/backend/tests/integration/test_admin_stories_endpoint.py`
  to assert `totalTokens` is present and correct in `GET /api/manage/stories` list
  responses (contracts/api.md)
- [X] T016 [US1] In `src/frontend/src/pages/AdminPage.jsx`, add a "Tokens" column: a
  `<th>` header and, per row, a `<td>` rendering `story.totalTokens` (defaulting to `0`)
  formatted with thousands separators (FR-003, FR-004, FR-010)
- [X] T017 [US1] [P] Update `src/frontend/tests/pages/AdminPage.test.jsx` for the Tokens
  column's rendering, the zero-token fallback, and thousands-separator formatting for a
  large total

**Checkpoint**: The stories list now shows an accurate, formatted cumulative token total
for every newly created story — User Story 1 is independently testable and demoable.

---

## Phase 4: User Story 2 - Find a story's last published date without cluttering the list (Priority: P2)

**Goal**: The always-visible last-published date moves behind a hover on the Published
status indicator, making room for the Tokens column without losing information.

**Independent Test**: Publish a story; confirm the stories list shows no inline
last-published text, but hovering the "Published" tag reveals the date. An unpublished
story's hover shows nothing and produces no error (quickstart.md Scenario 4).

### Implementation for User Story 2

- [X] T018 [US2] In `src/frontend/src/components/Admin/StoryPublishActions.jsx`, add a
  `hideStatusLine` prop that, when true, suppresses the inline "Status: … — last published
  …" text; leave rendering unchanged everywhere the prop is unset (research.md Decision 8)
- [X] T019 [US2] In `src/frontend/src/pages/AdminPage.jsx`, add a native `title` attribute
  to the Status cell's "Published"/"Unpublished" tag holding `story.lastPublishedAt`
  (formatted) **whenever it is set** — including a story now unpublished that was published
  before, since that past date doesn't change on unpublish — omitted only for a story with
  no `lastPublishedAt` (never published); pass `hideStatusLine` to `StoryPublishActions` in
  this row's usage (FR-005, FR-006, FR-007, Edge Cases)
- [X] T020 [US2] [P] Update
  `src/frontend/tests/components/StoryPublishActions.test.jsx`: `hideStatusLine`
  suppresses the inline text; default (unset) behavior is unchanged
- [X] T021 [US2] [P] Update `src/frontend/tests/pages/AdminPage.test.jsx`: the hover
  `title` attribute is present with the correct date for a published story **and** for a
  story unpublished after being published before; absent (no fabricated date, no error)
  only for a story that has never been published; and the inline last-published text no
  longer renders

**Checkpoint**: The stories list conveys both Published status (with date on hover) and
the new Tokens column without any new always-visible column — User Story 2 is
independently testable and demoable, and User Story 1's column now has room.

---

## Phase 5: User Story 4 - Review token usage per gameplay session (Priority: P2)

**Goal**: A new, read-only admin Sessions page lists every gameplay session (player and
admin test-play), each row showing story, session id, cumulative token total, and the
email of whoever played it.

**Independent Test**: Play (or test-play) a story for a few turns; open the new Sessions
page from the admin nav and confirm a row exists showing the story's name, a session
identifier, a non-zero token total, and the correct player/tester email (quickstart.md
Scenarios 5–8).

### Implementation for User Story 4

- [X] T022 [US4] In `src/backend/services/play_session_service.py`, update
  `_generate_and_persist_turn` to unpack `(payload, tokens)` from every
  `generate_gameplay_turn` call, set the new turn's `tokens` (`0` for a content-filtered
  deflection turn), and add `tokens` to `session.totalTokens` (data-model.md → PlaySession)
- [X] T023 [US4] In `src/backend/services/play_session_service.py`, update
  `_summarize_if_due` to unpack tokens from `summarize_session_history` and add them
  directly to `session.totalTokens`, without creating a turn record (research.md Decision 5)
- [X] T024 [US4] In `src/backend/services/play_session_service.py`, update
  `get_session_detail_for_player` to strip `tokens` from each turn dict in
  `summary["turns"]` before returning the response (research.md Decision 6); confirm
  `PlaySession.totalTokens` is not included in any player-facing response
- [X] T025 [US4] In `src/backend/services/story_service.py`, change
  `record_test_play(self, story_id: str, tokens_used: int)` to also add `tokens_used` to
  `Story.totalTokens` in the same read-modify-write that stamps `lastTestPlayedAt`
  (research.md Decision 3)
- [X] T026 [US4] In `src/backend/services/test_play_session_service.py`, update
  `_generate_and_persist_turn` to unpack `(payload, tokens)` from `generate_gameplay_turn`
  (`0` on the content-filtered branch), set the new exchange's `tokens`, add `tokens` to
  `session.totalTokens`, and pass the same `tokens` value to
  `self._stories.record_test_play(story.id, tokens)` — now that T025's signature accepts it
  (research.md Decision 3)
- [X] T027 [US4] Create `src/backend/services/session_overview_service.py`:
  `SessionOverviewService.list_sessions()` projecting both `playSessions` and
  `testPlaySessions` containers into the Session Overview Row shape, resolving story name
  live (fallback `"(deleted story)"`) and email via one `AccountProvisioningService.list_all()`
  in-memory `objectId -> email` index (fallback `"(no longer provisioned)"`) (data-model.md
  → Read model: Session Overview Row; research.md Decision 7)
- [X] T028 [US4] Create `src/backend/api/admin/sessions.py`: a `list_sessions` handler
  gated by `authorize_admin`, calling `SessionOverviewService.list_sessions()` and
  returning the `{"status": "success", "sessions": [...]}` shape (contracts/api.md → GET
  /api/manage/sessions)
- [X] T029 [US4] Register `GET manage/sessions` in `src/backend/function_app.py`, following
  the existing `@app.route(...)` + `_guarded(...)` pattern used by every other admin route
- [ ] T030 [US4] [P] Update `src/backend/tests/unit/test_play_session_service.py` for
  per-turn `tokens`, `session.totalTokens` accumulation (including summarization tokens and
  a zero-token content-filtered/turn-0 case), player-facing stripping in
  `get_session_detail_for_player`, and confirmation that no player-session tokens reach
  `Story.totalTokens`
- [ ] T031 [US4] [P] Update `src/backend/tests/unit/test_story_service.py` for `record_test_play`'s
  new `tokens_used` parameter and its `Story.totalTokens` increment (T025); and
  `src/backend/tests/unit/test_test_play_session_service.py` for per-exchange `tokens`,
  `session.totalTokens` accumulation, and the dual contribution to `Story.totalTokens` via
  `record_test_play`
- [X] T032 [US4] [P] Create `src/backend/tests/unit/test_session_overview_service.py`:
  combined player+test listing, the deleted-story fallback, the unprovisioned-account
  fallback, and a zero-turn session rendering `totalTokens: 0`
- [X] T033 [US4] [P] Create `src/backend/tests/integration/test_admin_sessions_endpoint.py`:
  the full `GET /api/manage/sessions` lifecycle, `401`/`403` without admin auth, and an
  empty-list `200` response
- [ ] T034 [US4] Create `src/frontend/src/services/sessionService.js`: `listSessions(token)`
  → `GET /manage/sessions`, following `accountService.js`'s axios/header pattern
- [ ] T035 [US4] Create `src/frontend/src/pages/AdminSessionsPage.jsx`: a read-only table
  with columns Story, Session ID, Total Tokens, Email — no create/edit/delete affordance
  anywhere on the page (FR-015, FR-016, FR-018)
- [ ] T036 [US4] In `src/frontend/src/App.jsx`, lazy-import `AdminSessionsPage` alongside
  the other admin pages and register its route at `/admin/sessions` behind
  `<ProtectedRoute capability="Administrator">`
- [ ] T037 [US4] In `src/frontend/src/components/Layout/NavBar.jsx`, add a "Sessions" link
  in the admin nav variant, alongside the existing Stories/New story/People links (FR-017)
- [ ] T038 [US4] [P] Update `src/frontend/tests/components/NavBar.test.jsx` to assert the
  Sessions link renders in the admin link set and gets `aria-current` on `/admin/sessions`,
  matching this file's existing per-link coverage of Stories/New story/People
- [ ] T039 [US4] [P] Create `src/frontend/tests/pages/AdminSessionsPage.test.jsx`: row
  rendering for both a player session and a test session, the deleted-story and
  unprovisioned-account fallbacks, and confirmation the page renders no edit/delete control

**Checkpoint**: The Sessions page is reachable from admin nav, lists every session
read-only with an accurate running total, and real player tokens still never reach
`Story.totalTokens` — User Story 4 is independently testable and demoable.

---

## Phase 6: User Story 3 - Token totals stay accurate across the whole story lifecycle (Priority: P3)

**Goal**: A story's cumulative total keeps growing correctly through edits/regenerations
and admin test plays, not just its first draft. (The test-play half of this story's
acceptance criteria is already satisfied by Phase 5's `record_test_play` change — this
phase adds the edit/regeneration half.)

**Independent Test**: Take a story with an existing token total; edit it in a way that
triggers content regeneration, save, then test-play it for a couple of exchanges; reload
the stories list and confirm the total increased to include both (quickstart.md
Scenario 2).

### Implementation for User Story 3

- [X] T040 [US3] In `src/backend/services/story_service.py`, change
  `_generate_narrative_guidance`, `_generate_starting_point`, and `derived_content` to
  unpack and accumulate the tokens spent by any LLM call they make, extending
  `DerivedContent` with a `tokens: int` field carrying that total (research.md Decision 2,
  edit/import case)
- [X] T041 [US3] In `src/backend/services/story_service.py`, update `apply_content_write`
  (used by both the wizard edit-save path and the id-matched import-overwrite path) to add
  `derived.tokens` onto the story's **existing** `totalTokens` when persisting — never
  replacing it. Note: the persisted object is actually built by the private
  `_replaced_story` helper, which today omits `totalTokens` entirely — it MUST also be
  updated to carry `current.totalTokens + derived.tokens` forward, or every edit-save and
  id-matched import-overwrite will silently reset the story's total to `0` (research.md
  Decision 2)
- [X] T042 [US3] In `src/backend/services/story_service.py`, update `import_configuration`'s
  new-story branch (no `configuration.id`) to set the new `Story.totalTokens = derived.tokens`
  — this branch builds its `Story(...)` directly, bypassing `apply_content_write`/
  `_replaced_story`, so T041's fix does not cover it (research.md Decision 2)
- [X] T043 [US3] In `src/backend/services/story_service.py`, update `ensure_starting_point`
  to add its backfill call's tokens to `Story.totalTokens` before the read-modify-write
  persist; on a lost `_etag` race, accept the resulting undercount rather than retrying
  (research.md Decision 2, accepted per Principle XII)
- [X] T044 [US3] In `src/backend/services/story_draft_service.py`, update
  `save_draft_to_story` to add the edit draft's accumulated `totalTokens` plus
  `derived_content`'s regeneration tokens (T040/T041) onto the existing story's
  `totalTokens` (research.md Decision 2, edit case)
- [X] T045 [US3] [P] Update `src/backend/tests/unit/test_story_service.py` for
  `derived_content`/`ensure_starting_point`/`apply_content_write`/`import_configuration`
  token accumulation, including: the accepted etag-race undercount case, a concurrent
  edit-vs-test-play case proving `_replaced_story` carries `totalTokens` forward (T041),
  and an import creating a new story that also generated content (T042)
- [X] T046 [US3] [P] Update `src/backend/tests/unit/test_story_draft_service.py` for
  `save_draft_to_story` folding both the draft's and the regeneration's tokens into the
  existing story's total
- [X] T047 [US3] [P] Update `src/backend/tests/integration/test_admin_stories_endpoint.py`
  with an edit-then-test-play-then-reload scenario showing `totalTokens` reflects both
  increases

**Checkpoint**: A story's token total is now trustworthy across its entire authoring
lifecycle — creation, every edit/regeneration, and every test play — satisfying User
Story 3 end-to-end.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Whole-feature verification once every story phase is complete.

- [ ] T048 [P] Run the full backend pytest suite and the full frontend Vitest suite;
  confirm both are green (Principle V, Constitution Check)
- [ ] T049 Walk through quickstart.md Scenarios 1–8 end-to-end against a running dev
  instance, confirming SC-001 through SC-006
- [ ] T050 [P] Spot-check the Edge Cases in spec.md not already covered by a specific
  story's tests: a very large `totalTokens` still renders with thousands separators
  (FR-010), a session still in progress renders its running total, and a session whose
  story was deleted still renders using the `"(deleted story)"` fallback

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately, and can also run any time
  before this feature's PR is opened (it touches no application code).
- **Foundational (Phase 2)**: No dependencies — BLOCKS every user story phase's backend
  tasks (T009+), since they all consume the `(payload, tokens_used)` tuple T007 introduces.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on nothing but Foundational's model fields being
  absent from its own scope — it is a pure frontend change and could in practice run in
  parallel with Phase 3, but is sequenced second to match its P2 priority.
- **User Story 4 (Phase 5)**: Depends on Foundational only. Implements the
  `record_test_play(story_id, tokens_used)` signature change (T025) that Phase 6 relies on.
- **User Story 3 (Phase 6)**: Depends on Foundational, and on Phase 5's T025/T026 for its
  test-play acceptance scenario (the edit/regeneration half, T040-T044, has no dependency
  on Phase 5 and could be built first if reordered).
- **Polish (Phase 7)**: Depends on all four user story phases being complete.

### Parallel Opportunities

- All of T002-T006 (Foundational model/config fields) can run in parallel — five different
  files, no shared state.
- Within User Story 1: T013, T014, T015, T017 (four different test files) can run in
  parallel once their corresponding implementation tasks land.
- Within User Story 2: T020 and T021 (two different test files) can run in parallel.
- Within User Story 4: T030, T031, T032, T033 (backend test files) can run in parallel once
  T022-T029 land; T038 (once T037 lands) and T039 (once T035 lands) can run alongside those.
- Within User Story 3: T045 and T046 (two different test files) can run in parallel.
- User Story 2 (Phase 4, pure frontend) can be staffed in parallel with User Story 1
  (Phase 3, pure backend + one frontend column) by a second developer once Foundational is
  done, despite the sequential listing above.

---

## Parallel Example: Foundational Phase

```bash
# Launch all four model/config field additions together:
Task: "Add totalTokens to Story in src/backend/models/story.py"
Task: "Add totalTokens to StoryDraft in src/backend/models/story_draft.py"
Task: "Add totalTokens/tokens to PlaySession/PlayerInteraction in src/backend/models/play_session.py"
Task: "Add totalTokens/tokens to TestPlaySession/TestPlayExchange in src/backend/models/test_play_session.py"
Task: "Add totalTokens to SYSTEM_MANAGED_KEYS in src/backend/services/story_config_file.py"
```

## Parallel Example: User Story 4 tests

```bash
# Once T022-T029 are implemented, launch these test-file updates together (T031 touches two files):
Task: "Update test_play_session_service.py for per-turn tokens and session totals"
Task: "Update test_story_service.py for record_test_play's new tokens_used param"
Task: "Update test_test_play_session_service.py for per-exchange tokens and dual Story contribution"
Task: "Create test_session_overview_service.py for combined listing and fallbacks"
Task: "Create test_admin_sessions_endpoint.py for the full endpoint lifecycle"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (constitution amendment — can also be deferred to just before
   the PR, since it gates Phase 5's screen, not Phase 3).
2. Complete Phase 2: Foundational (CRITICAL — blocks every story).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: quickstart.md Scenario 1 — a newly created story shows a
   non-zero token total on the stories list.
5. Deploy/demo if ready — this alone delivers the feature request's core value.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate independently → demo (MVP!).
3. Add User Story 2 → validate independently → demo (list now has both Tokens and the
   hover date, no new always-visible column).
4. Add User Story 4 → validate independently → demo (Sessions page live, nav updated,
   constitution amendment landed).
5. Add User Story 3 → validate independently → demo (totals now correct across the full
   lifecycle, including the test-play half already exercised by Story 4).
6. Phase 7 Polish → full-suite green, quickstart.md walked end-to-end.

### Suggested MVP Scope

**User Story 1** (Phase 3, on top of Setup + Foundational) is the suggested MVP: it is the
single change the original feature request was for (SC-001), is independently testable
today, and needs neither the hover relayout (US2) nor the Sessions page (US4) to deliver
value.
