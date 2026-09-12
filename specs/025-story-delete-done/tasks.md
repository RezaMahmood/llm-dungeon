---

description: "Task list for Story Delete (025-story-delete)"
---

# Tasks: Story Delete

**Input**: Design documents from `/specs/025-story-delete/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: Constitution Principle I (NON-NEGOTIABLE) requires an automated test for every functionality and edge case; spec.md's FR-014 explicitly enumerates the outcomes needing one. Test tasks are included throughout.

**Organization**: Tasks are grouped by user story. US2 depends on US1 existing (a story must be deletable before its half of this behavior can be observed). US1 alone is a shippable increment: it permanently removes a story's configuration and its list row. US2 then adds two genuinely different mechanisms sharing one spec: a **delete cascade** (permanently removes sessions) and an **unpublish availability check** (never touches a session, only blocks continuation, computed live) — these must stay distinct in the implementation, not be merged into one "unavailable" code path.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Existing web-application layout: `src/backend/` (Python Azure Functions) + `src/frontend/` (React SPA via Vite), per plan.md. This feature extends existing files only — no new services, models, or containers.

---

## Phase 1: Setup

**Purpose**: Confirm the feature's foundation is where plan.md/data-model.md assume it to be before extending it.

- [X] T001 Verify `src/backend/services/story_service.py`, `src/backend/services/play_session_service.py`, `src/backend/models/story.py`, `src/backend/models/play_session.py`, `src/backend/api/admin/stories.py`, `src/backend/api/game/sessions.py`, `src/backend/function_app.py`, `src/frontend/src/pages/AdminPage.jsx`, `src/frontend/src/pages/PlayPage.jsx`, `src/frontend/src/components/Admin/StoryPublishActions.jsx`, `src/frontend/src/hooks/usePublishToggle.js`, `src/frontend/src/components/GameSetup/SavedGameRow.jsx`, `src/frontend/src/components/GameSetup/StoriesInProgress.jsx`, `src/frontend/src/services/gameService.js`, and `src/frontend/src/services/storyDraftService.js` are present and match the shapes plan.md/data-model.md/research.md assume; note any drift before proceeding. No file changes in this task.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: This feature adds no new entity, field, or container (data-model.md) — there is no shared schema migration or scaffolding to stand up beyond Phase 1's verification.

**⚠️ CRITICAL**: No user story work can begin until Phase 1 is complete.

*(No additional foundational tasks — Phase 1 alone is the prerequisite for both user stories.)*

---

## Phase 3: User Story 1 - Administrator Permanently Deletes a Story (Priority: P1) 🎯 MVP

**Goal**: An administrator can permanently delete a story from the admin story list, behind a destructive-action confirmation distinct from unpublish's, with the story's configuration record removed from the datastore and its row removed from the list in place.

**Independent Test**: From the story list, choose delete on a story with no active player sessions, confirm the destructive-action prompt, and verify the story record no longer exists in the datastore and no longer appears in the administrator's story list.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation.

- [X] T002 [P] [US1] Unit tests for `StoryService.delete_story` in `src/backend/tests/unit/test_story_service.py`: deleting an existing story removes it (a subsequent `get_story` returns `None`); deleting a nonexistent story id returns `False`/reports not-found rather than raising; deletion succeeds regardless of `published` (test both `True` and `False`) (data-model.md State Transitions, contracts/api.md Validation Rules).
- [X] T003 [P] [US1] Integration tests for `DELETE /api/manage/stories/{storyId}` in `src/backend/tests/integration/test_admin_stories_delete_endpoint.py` (new file, following the `FakeCosmosService`/`_patched_authorize_admin` pattern in `test_admin_stories_publish_endpoint.py`): 200 `{"status": "deleted", "storyId": ...}` for an existing story, and a subsequent `GET .../{storyId}` on the same id returns 404; 404 `not_found` for a story id that never existed; 404 `not_found` (not a fresh 200) when deleting an already-deleted story a second time; deletion succeeds for both a published and an unpublished story; unauthenticated/non-admin requests are rejected (Principle II) (contracts/api.md, spec.md Edge Cases, SC-001).

### Implementation for User Story 1

- [X] T004 [US1] Add `delete_story(self, story_id: str) -> bool` to `src/backend/services/story_service.py`: call `self._container().delete_item(item=story_id, partition_key=story_id)`, catching `CosmosResourceNotFoundError` and returning `False`; return `True` on success (research.md Decision 1, data-model.md) (depends on T002 existing as a failing test).
- [X] T005 [US1] Add a `delete_story` handler to `src/backend/api/admin/stories.py`, following the existing `publish_story`/`unpublish_story` pattern: `authorize_admin` guard, `story_id = req.route_params.get("storyId")`, call `StoryService.delete_story(story_id)`; on `False` return `error_response(404, "not_found", "Story not found")`; on `True` return `json_response({"status": "deleted", "storyId": story_id}, status_code=200)` (contracts/api.md) (depends on T004).
- [X] T006 [US1] Register `DELETE manage/stories/{storyId}` in `src/backend/function_app.py`, importing `delete_story` alongside the existing `backend.api.admin.stories` imports and wiring it through the same `_guarded(...)` wrapper used by `admin_stories_get`/`admin_stories_publish` (depends on T005).
- [X] T007 [US1] Add `deleteStory(token, storyId)` to `src/frontend/src/services/storyDraftService.js`, following the existing `publishStory`/`unpublishStory` pattern (`client.delete(`/manage/stories/${storyId}`, authHeaders(token))`, returning `response.data`), and export it from the file's default export object (depends on T006).
- [X] T008 [US1] Create `src/frontend/src/hooks/useDeleteStory.js`, mirroring `usePublishToggle.js`'s shape: `status` (`idle|working|error`), `confirmingDelete` state, `requestDelete`/`confirmDelete`/`cancelDelete`, calling `deleteStory` on confirm and invoking an `onDeleted?.(story.id)` callback (no `onStoryChange` with an updated story — there is nothing left to describe, per contracts/api.md) (research.md Decision 7) (depends on T007).
- [X] T009 [US1] Create `src/frontend/src/components/Admin/StoryDeleteAction.jsx`, mirroring `StoryPublishActions.jsx`'s `.dialog`/`.dialog-backdrop`/`role="dialog"`/`aria-modal`/`aria-labelledby` pattern via `useDeleteStory`: a "Delete" button that opens the confirmation dialog; dialog copy explicitly distinct from the unpublish dialog's, stating the action is **permanent, cannot be undone, and will remove any players' in-progress games for this story** (FR-002); "Keep it" / "Delete" actions, disabled while `status === "working"` (depends on T008).
- [X] T010 [US1] Wire `StoryDeleteAction` into `src/frontend/src/pages/AdminPage.jsx`'s per-row actions, alongside the existing `StoryPublishActions`; on successful delete, remove that story from the `stories` state array (FR-012 — no full list reload) via a new callback analogous to `handleStoryChange` (e.g. `handleStoryDeleted`) (depends on T009).
- [X] T011 [P] [US1] Component tests for `StoryDeleteAction` in `src/frontend/tests/components/StoryDeleteAction.test.jsx` (mirroring `StoryPublishActions.test.jsx`): clicking Delete opens the confirmation dialog and does not call `deleteStory` until confirmed; the dialog's copy states the action is permanent/irreversible; confirming calls `deleteStory` and invokes the deleted callback; canceling leaves state unchanged and calls nothing (depends on T009).
- [X] T012 [P] [US1] Integration test `src/frontend/tests/integration/admin_stories_list_delete.test.jsx` (mirroring `admin_stories_list_publish.test.jsx`) against a mocked API: deleting a row removes it from the rendered list in place, with no refetch of the full list; cancelling the confirmation leaves the row in place and calls no API; only the acted-on row is affected when several stories are listed (SC-001, SC-004) (depends on T010).

**Checkpoint**: User Story 1 is fully functional and independently testable — an administrator can permanently delete a story (published or not) from the story list, behind a distinct destructive confirmation, with the datastore record and the list row both gone.

---

## Phase 4: User Story 2 - A Player's In-Progress Session Ends Gracefully When Its Story Becomes Unavailable (Priority: P2)

**Goal**: Deleting a story (Phase 3's action) permanently removes every in-progress player session against it; unpublishing a story leaves every in-progress session against it completely intact but non-continuable. Either way, the player only discovers this lazily — on their next turn, resume, or list load — and is told the specific reason. This phase's two mechanisms (delete cascade vs. live-computed unpublish check) are independent of each other and must not be collapsed into one.

**Independent Test**: Start a game as a player against a story. (a) Have an administrator unpublish it, submit the next turn, verify a specific "Story has been unpublished" message with a prompt to return to the list, and verify the game still appears in the list, greyed out. (b) With a different session, have an administrator delete the story, submit the next turn, verify a specific "Story has been deleted" message with the same prompt, and verify the game's persisted session and its list entry are both gone.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation.

- [X] T013 [P] [US2] Unit tests for `PlaySessionService.delete_active_sessions_for_adventure` in `src/backend/tests/unit/test_play_session_service.py`: removes every `status == 'active'` session for the given `adventureId` across multiple players; leaves `status == 'concluded'` sessions for that same `adventureId` untouched; leaves active sessions for a *different* `adventureId` untouched; returns/reports the count removed (data-model.md Cascade on Delete, spec.md Edge Cases).
- [X] T014 [P] [US2] Unit tests for the new story-unpublished check in `src/backend/tests/unit/test_play_session_service.py`: `submit_interaction` against an active session whose story is unpublished (but exists) raises `StoryUnpublishedError` and leaves the session document byte-for-byte unchanged (no write); the same story published again lets the next `submit_interaction` proceed normally with no special handling; `resume_session` and `get_session_detail_for_player` raise the same error under the same condition (data-model.md Live Availability on Unpublish, research.md Decision 4).
- [X] T015 [P] [US2] Unit tests for `PlaySessionService.list_player_sessions`'s new `available` field in `src/backend/tests/unit/test_play_session_service.py`: a session whose story is published returns `available: True`; a session whose story is unpublished returns `available: False`; after that story is re-published, the same call returns `available: True` again with no other change (research.md Decision 5, FR-011).
- [X] T016 [P] [US2] Integration test additions to `src/backend/tests/integration/test_game_sessions_endpoint.py`: submitting an interaction, resuming, or reading detail against a session whose story was deleted returns `404 {"error": "story_deleted", "message": "Story has been deleted. You can no longer continue this story.", "promptReturnToList": true}`; the same three requests against a session whose story was merely unpublished return `409 {"error": "story_unpublished", ...}` instead, and the session's turn history is unchanged afterward (contracts/api.md).
- [X] T017 [P] [US2] Integration tests in `src/backend/tests/integration/test_admin_stories_delete_endpoint.py` covering the full delete cascade via HTTP: deleting a story that has one active `PlaySession` also permanently removes that session (a subsequent read/list for it returns nothing); deleting a story with sessions from *multiple* players removes all of them; deleting a story with a *concluded* session for it leaves that session in place (Edge Cases); deleting a story with no sessions at all still succeeds (spec.md Acceptance Scenario 8) (quickstart.md Scenario 4).

### Implementation for User Story 2

- [X] T018 [US2] Add `delete_active_sessions_for_adventure(self, adventure_id: str) -> int` to `src/backend/services/play_session_service.py`: cross-partition query `SELECT c.id FROM c WHERE c.adventureId = @adventureId AND c.status = 'active'` (mirroring `list_player_sessions`'s query shape), then `self._container().delete_item(item=row["id"], partition_key=row["id"])` per row; return the count removed (research.md Decision 2, data-model.md) (depends on T013 existing as a failing test).
- [X] T019 [US2] In `src/backend/api/admin/stories.py`'s `delete_story` handler (T005), after a successful `StoryService.delete_story`, call `PlaySessionService().delete_active_sessions_for_adventure(story_id)` (composing the two services at the handler level, not inside `StoryService`, per research.md Decision 6 — avoids a circular import since `PlaySessionService` already imports `StoryService`); the handler's response shape (`{"status": "deleted", "storyId": ...}`) is unchanged (depends on T018, T005).
- [X] T020 [US2] Add a new `StoryUnpublishedError` exception to `src/backend/services/play_session_service.py`, and a shared internal check (e.g. `_check_story_available(session)`) that: reads the session's story via `self._stories.get_story(session.adventureId)`; raises `AdventureNotFoundError` if `story is None` (existing behavior, unchanged — the narrow race case); raises `StoryUnpublishedError` if `story is not None and not story.published`; otherwise returns normally without mutating the session. Call this check from `submit_interaction` (inside `_generate_and_persist_turn`, replacing its existing bare `story is None` check), `resume_session`, and `get_session_detail_for_player`, in each case before any write or narrative generation (research.md Decision 4, data-model.md) (depends on T014 existing as a failing test).
- [X] T021 [US2] Extend `PlaySessionService.list_player_sessions` to batch-resolve each distinct `adventureId`'s current `published` value alongside its existing name resolution (reusing `StoryService.get_adventure_summary`'s `published` field), and add `available: bool` to each returned row (research.md Decision 5) (depends on T015 existing as a failing test).
- [X] T022 [US2] In `src/backend/api/game/sessions.py`, map `SessionNotFoundError` and `AdventureNotFoundError` (in `submit_interaction`, `resume_session`, and the session-detail read handler) to `error_response(404, "story_deleted", "Story has been deleted. You can no longer continue this story.")` with `promptReturnToList: true` added to the body; map the new `StoryUnpublishedError` to `error_response(409, "story_unpublished", "Story has been unpublished. You can no longer continue this story.")` with the same `promptReturnToList: true` (contracts/api.md) (depends on T020, T016 existing as a failing test).
- [X] T023 [US2] Pass `available` through in the list-sessions API handler in `src/backend/api/game/sessions.py` (or wherever `list_player_sessions`'s result is serialized to the response) unchanged, so each row in `GET /api/game/sessions` carries the new field (depends on T021).
- [X] T024 [P] [US2] Add two new notice branches to `src/frontend/src/pages/PlayPage.jsx`'s `handleSubmit` error handling, alongside the existing `429`/`409 interaction_in_progress`/`409 session_inactive`/`423`/`409 session_concluded` branches: `err.response.status === 404 && body?.error === "story_deleted"` renders "Story has been deleted. You can no longer continue this story." with a "Return to your story list" action; `err.response.status === 409 && body?.error === "story_unpublished"` renders "Story has been unpublished. You can no longer continue this story." with the same action (FR-007, FR-008) (depends on T022).
- [X] T025 [P] [US2] Update `src/frontend/src/components/GameSetup/SavedGameRow.jsx` to render a row whose `session.available === false` visually greyed out (e.g. reduced-opacity/`text-muted` styling, existing tokens only per Principle VIII) with its Resume button disabled or replaced with an "Unavailable" indicator, instead of its normal continuable state (FR-009) (depends on T023).
- [X] T026 [P] [US2] Test additions to `src/frontend/tests/Play/PlayPage.test.jsx`: submitting a turn that receives a `404 story_deleted` response renders the specific "deleted" notice with the return-to-list action; one receiving `409 story_unpublished` renders the specific "unpublished" notice with the same action; neither falls into the generic error notice (depends on T024).
- [X] T027 [P] [US2] Test additions to `src/frontend/tests/components/GameSetup/StoriesInProgress.test.jsx`: a row with `available: false` renders greyed out and non-continuable; a row with `available: true` (or the field absent, for backward compatibility with any pre-existing fixture data) renders normally; re-rendering with `available` flipped back to `true` (simulating a re-publish) restores the normal row with no other state change (FR-009, FR-011, SC-005) (depends on T025).

**Checkpoint**: All user stories are independently functional — deleting a story permanently removes every in-progress session against it; unpublishing a story leaves sessions intact but non-continuable and visibly greyed out, automatically restored on re-publish. Any affected player sees the correct, specific notice on their next turn, resume, or list load.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Close out validation that spans both stories.

- [X] T028 Run the full backend (`pytest`) and frontend (`vitest`) suites and fix any regressions introduced by T002–T027.
- [X] T029 Walk through quickstart.md Scenarios 1–7 manually against a local run; confirm SC-001 through SC-005 hold, including the multi-player delete cascade in Scenario 4, the unpublish/greyed-out/restore cycle in Scenario 5, and the concluded-session exception in Scenario 6.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: No additional tasks; Phase 1 alone is the prerequisite.
- **User Story 1 (Phase 3)**: Depends on Phase 1. Fully independent of US2's own tasks — deletable without any session-cascade or unpublish-check change in place yet (a delete of a story with no active sessions is US1's full independent test).
- **User Story 2 (Phase 4)**: Depends on Phase 1. Only T019 (which edits the `delete_story` handler to add the cascade call) functionally depends on US1's T005 existing — do not start T019 before T005 lands. T018, T020, and T021 touch only `play_session_service.py` and have no dependency on T005, so they may proceed as soon as their own failing tests (T013, T014, T015) exist, in parallel with all of Phase 3. Phase 4's tests (T013–T017) may likewise be written in parallel with Phase 3 once Phase 1 is done.
- **Polish (Phase 5)**: Depends on both US1 and US2 being complete.

### Within Phase 3

- Tests (T002, T003) should be written and failing before implementation (T004–T010).
- T004 (service layer) before T005 (API handler) before T006 (route registration) before T007 (frontend API call) before T008 (hook) before T009 (component) before T010 (page wiring).
- T011, T012 (frontend tests) depend on T009/T010 being in place, and may run in parallel with each other (different files).

### Within Phase 4

- Tests (T013–T017) should be written and failing before implementation (T018–T027).
- Three independent threads touch `play_session_service.py`/`api/game/sessions.py`: the delete-cascade thread (T018 → T019), the unpublish-block thread (T020 → T022 → T024 → T026), and the availability-flag thread (T021 → T023 → T025 → T027). They touch different methods/handlers and are logically independent — implement in any order, or in parallel if multiple people are working the file (coordinate to avoid edit conflicts).
- T022 depends on T020 (the new exception) and T016 (existing as a failing test). It does NOT depend on T019 — T019 edits `api/admin/stories.py` while T022 edits `api/game/sessions.py`, so there is no file conflict or ordering requirement between them.
- T024 (frontend notice) depends on T022 (the response shapes it renders). T025 (greyed-out row) depends on T023 (the `available` field reaching the frontend). T026 depends on T024; T027 depends on T025.

### Parallel Opportunities

- T002 and T003 (Phase 3 backend tests, different files) can be written in parallel.
- T011 and T012 (Phase 3 frontend tests, different files) can run in parallel once T009/T010 land.
- T013, T014, T015, T016, and T017 (Phase 4 tests, mostly different files/sections) can largely be written in parallel — T013/T014/T015 share `test_play_session_service.py` but cover disjoint methods.
- T018 and T020 (different methods in the same service file) can proceed in parallel once their respective tests exist, so long as edits are coordinated to avoid clobbering each other in the same file — and, per the Phase Dependencies note above, neither needs to wait for T005/Phase 3.
- T024 and T025 (different files — `PlayPage.jsx` vs. `SavedGameRow.jsx` — with independent dependency chains through T022 and T023 respectively) can proceed in parallel once their own prerequisites land.
- T026 and T027 (different frontend test files) can run in parallel.

---

## Parallel Example: Phase 3 Tests

```bash
# Launch backend and frontend test-writing together (different files, no shared dependency):
Task: "Unit tests for delete_story in src/backend/tests/unit/test_story_service.py"
Task: "Integration tests for DELETE .../{storyId} in src/backend/tests/integration/test_admin_stories_delete_endpoint.py"
```

## Parallel Example: Phase 4 Tests

```bash
# These touch different files (or disjoint sections of the same file) and can be written together:
Task: "delete_active_sessions_for_adventure unit tests in src/backend/tests/unit/test_play_session_service.py"
Task: "story-unpublished check unit tests in src/backend/tests/unit/test_play_session_service.py"
Task: "list_player_sessions available-field unit tests in src/backend/tests/unit/test_play_session_service.py"
Task: "story_deleted/story_unpublished response assertions in src/backend/tests/integration/test_game_sessions_endpoint.py"
Task: "Delete-cascade-via-HTTP tests in src/backend/tests/integration/test_admin_stories_delete_endpoint.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (verification only — no foundational tasks).
2. Complete Phase 3 (User Story 1): an administrator can permanently delete a story, distinct from unpublish, with its list row and datastore record both gone. This alone satisfies spec.md's Independent Test for US1 and SC-001/SC-004.
3. **STOP and VALIDATE**: exercise quickstart.md Scenarios 1–3 and 7.
4. Deploy/demo if ready — note that, until Phase 4 lands, deleting a story with active player sessions leaves those sessions orphaned (their next turn will hit the old generic error, and unpublish still behaves per its pre-existing, now-superseded implementation) — an explicitly tracked interim gap, not a silent one.

### Incremental Delivery

1. Phase 1 → foundation confirmed.
2. Phase 3 → delete is fully usable from the story list (MVP).
3. Phase 4 → the delete cascade and the unpublish availability/messaging behavior are both complete; the interim gap above is closed.
4. Phase 5 → full-suite validation and the complete quickstart walkthrough.

---

## Notes

- Delete and unpublish are implemented by two genuinely different mechanisms in Phase 4 and must stay that way: `delete_active_sessions_for_adventure` (T018) permanently removes rows; the story-unpublished check (T020) never writes to a session at all. Do not collapse these into a single "mark unavailable" code path.
- `[P]` tasks touch different files (or clearly disjoint sections of the same file) with no unresolved dependency between them.
- Commit after each task or logical group; stop at the Phase 3 checkpoint to validate User Story 1 independently before starting Phase 4.

---

## Phase 6: Convergence

- [X] T030 Add `story_deleted` (404) and `story_unpublished` (409) branches to `handleResume`'s `catch` in `src/frontend/src/pages/GamePage.jsx`, which currently collapses every failure from `resumeSession` *and* `getSession` into the generic `"Couldn't resume this story. Please try again."`. Both calls can now return those two bodies (`src/backend/api/game/sessions.py` `resume_session` / `get_session`), and this is the primary path by which a player meets a deleted or unpublished story — they must return to the list and click Resume before they could ever submit a turn. Render each as its own specific message (the response body's `message`, matching `PlayPage.jsx`'s two notice branches) instead of the shared generic one; the player is already on their in-progress-games list here, so `promptReturnToList`'s call to action is satisfied by staying put — do not add a second navigation control. Also drop the now-stale row from `savedGames` state on `story_deleted`, per `FR-010` per contracts/api.md "Changed: POST /api/game/sessions/{sessionId}/resume", "Changed: GET session detail", and their shared Validation Rules ("The frontend MUST render `story_deleted` and `story_unpublished` as two distinct, specific notices — not a shared generic message"), FR-007, FR-008 (partial)
- [X] T031 Add integration test coverage for T030's two outcomes in `src/frontend/tests/integration/save_and_continue.test.jsx`, alongside its existing `"shows an error and stays on the stories screen when resume genuinely fails"` case (which asserts only the generic message): clicking Resume on a row whose story was deleted renders the specific "Story has been deleted…" notice and removes that row; clicking Resume on one whose story was unpublished renders the specific "Story has been unpublished…" notice; neither falls into the generic `"couldn't resume this story"` branch. Cover the failure arriving from `getSession` as well as from `resumeSession`, since `handleResume` calls both inside one `try` per FR-014 (every distinct outcome needs an automated test) and Constitution Principle I (missing)
