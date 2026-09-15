---

description: "Task list for Remembering and Showing a Player's Avatar"
---

# Tasks: Remembering and Showing a Player's Avatar

**Input**: Design documents from `/specs/034-avatar-memory-and-visibility/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: FR-013 requires an automated test for every behavior this slice introduces — test
tasks are included throughout.

**Organization**: User Story 1 (show, P1) and User Story 2 (remember, P2) are independent per
spec.md's *Relationship to the other slices* and may ship in either order; Setup below is a
shared prerequisite for both.

## Phase 1: Setup

- [x] T001 [P] Fix `createSession`'s stale `characterType` destructuring to `avatarDescription`
      (request param and body) in `src/frontend/src/services/gameService.js` (research.md
      Decision 7) — a prerequisite for both stories: neither US1's session-carried description
      nor US2's stored-for-prefill description exists if the description never reaches the
      backend.
- [x] T002 [P] Add `STORED_AVATAR_DESCRIPTIONS_CONTAINER = "storedAvatarDescriptions"` constant
      in `src/backend/config.py`, alongside `AVATAR_SETUP_ATTEMPTS_CONTAINER`.
- [x] T003 [P] Add `azurerm_cosmosdb_sql_container.stored_avatar_descriptions` (partition key
      `/id`, version 2, no TTL) and its `STORED_AVATAR_DESCRIPTIONS_CONTAINER` app-setting entry
      in `infrastructure/terraform/main.tf`, mirroring the `avatar_setup_attempts` resource.

**Checkpoint**: Both user stories can now be built in either order.

## Phase 2: User Story 1 - A Player Can See Who They Are (Priority: P1)

**Goal**: The player's own avatar description is shown read-only in the play surface's status
panel, alongside location, goal, and progress; a session with none renders cleanly.

**Independent Test**: Start a session with a distinctive description, play a few turns, and
verify the description is readable in the status panel and that location, goal, and progress
remain reachable alongside it (per quickstart.md).

- [x] T004 [P] [US1] Add `avatarDescription` to the response shape built in
      `get_session_detail_for_player` in `src/backend/services/play_session_service.py`
      (`summary["avatarDescription"] = session.avatarDescription`, alongside `characterType`/
      `status`/`completionReason`).
- [x] T005 [P] [US1] Unit test: `get_session_detail_for_player` includes the session's own
      `avatarDescription`, and `None` for a session built with none, in
      `src/backend/tests/unit/test_play_session_service.py`.
- [x] T006 [US1] Add an `avatarDescription` prop and a read-only "Who you are" section to
      `src/frontend/src/components/Play/StatusPanel.jsx`, guarded by the same
      `{value && (...)}` conditional pattern the panel already uses for `goalLabel`/`progress`
      so a missing description renders no empty/broken area (FR-003).
- [x] T007 [P] [US1] Component tests in `src/frontend/tests/components/Play/StatusPanel.test.jsx`
      (new file if it doesn't exist): renders the description when provided; renders no avatar
      section when absent; location/goal/progress remain present alongside a 500-character
      description.
- [x] T008 [US1] Thread `avatarDescription` through `src/frontend/src/pages/PlayPage.jsx` as a
      prop into `<StatusPanel>`.
- [x] T009 [US1] Thread `avatarDescription` through `src/frontend/src/pages/GamePage.jsx`: include
      it in the `session` state set on fresh session creation (already held locally from the
      setup form) and in the `session` state set on resume (`data.session.avatarDescription`,
      from T004's response shape); pass it to `<PlayPage>`.
- [x] T010 [P] [US1] Integration test extending
      `src/frontend/tests/integration/game_setup_flow.test.jsx` (or a new
      `play_status_panel.test.jsx`): after starting a session, the status panel shows the typed
      avatar description.
- [x] T011 [P] [US1] Integration test: resuming a session whose `avatarDescription` is `None`
      (a pre-`032` session) renders the status panel with no avatar section and no error.

**Checkpoint**: User Story 1 is independently complete and testable.

## Phase 3: User Story 2 - A Returning Player Does Not Retype (Priority: P2)

**Goal**: A player's avatar description is remembered per adventure against their own profile,
offered back as an editable prefill next time, revalidated on submission, deleted with its
adventure, and untouched by session deletion.

**Independent Test**: Play an adventure, exit, start a new game of the same adventure, and
verify the previous description is prefilled and fully editable (per quickstart.md).

- [x] T012 [P] [US2] Create `StoredAvatarDescription` dataclass (`id`, `playerId`, `storyId`,
      `description`, `updatedAt`, `entityType`) with `to_dict`/`from_dict` in
      `src/backend/models/stored_avatar_description.py` (data-model.md).
- [x] T013 [US2] Create `StoredAvatarDescriptionService` in
      `src/backend/services/stored_avatar_description_service.py` with `get(player_id, story_id)
      -> Optional[str]`, `store(player_id, story_id, description) -> None` (upsert, bounded
      `_etag` read-modify-write, same shape as `AvatarSetupAttemptsService.record_attempt`), and
      `delete_for_story(story_id) -> int` (query by `storyId`, delete each row, tolerate
      `CosmosResourceNotFoundError` per row — mirrors
      `delete_active_sessions_for_adventure`).
- [x] T014 [P] [US2] Unit tests for `StoredAvatarDescriptionService` in
      `src/backend/tests/unit/test_stored_avatar_description_service.py`: store-then-get
      round-trip; a second `store` for the same pair replaces rather than accumulates;
      `delete_for_story` removes only rows for that `storyId` and tolerates a missing row.
- [x] T015 [US2] In `PlaySessionService.create_session`
      (`src/backend/services/play_session_service.py`), after the session document is
      successfully created (alongside the existing `clear_attempts` call), call
      `StoredAvatarDescriptionService.store(player_id, story.id, validated_avatar)`. Add a
      `stored_avatar_description_service` constructor parameter (optional, defaulted) following
      this class's existing dependency-injection pattern.
- [x] T016 [P] [US2] Unit test: `create_session` stores the description on success and does not
      call `store` on any failure path (adventure not found, lockout, rate-limited,
      format/relevance rejection) in `src/backend/tests/unit/test_play_session_service.py`.
- [x] T017 [US2] In `get_adventure` (`src/backend/api/game/adventures.py`), read
      `StoredAvatarDescriptionService.get(user_oid, adventure_id)` and include it as
      `adventure.avatarDescription` (`None` if absent) in the response.
- [x] T018 [P] [US2] Unit test for `get_adventure`: returns the caller's own stored description;
      returns `None` when none exists; a second player's request for the same adventure never
      returns the first player's description, in `src/backend/tests/unit/test_game_adventures.py`.
- [x] T019 [US2] In `delete_story` (`src/backend/api/admin/stories.py`), call
      `StoredAvatarDescriptionService.delete_for_story(story_id)` alongside the existing
      `sessions.delete_active_sessions_for_adventure(story_id)` call.
- [x] T020 [P] [US2] Unit test: deleting a story removes every stored description for it and
      leaves `Story.totalTokens` unchanged, in `src/backend/tests/unit/test_admin_stories.py`
      (or the equivalent existing delete-cascade test module).
- [x] T021 [P] [US2] Unit test: deleting a session (`delete_session_as_administrator` /
      the player's own delete path) leaves that player's stored description for the adventure
      untouched, in `src/backend/tests/unit/test_play_session_service.py`.
- [x] T022 [US2] In `src/frontend/src/pages/GamePage.jsx`, prefill `avatarDescription` state from
      `getAdventure`'s response in the existing adventure-name-fetching effect, using a
      functional `setAvatarDescription(prev => prev === "" ? (data.adventure?.avatarDescription
      || "") : prev)` so a slow response never overwrites text the player has already started
      typing.
- [x] T023 [P] [US2] Integration test extending
      `src/frontend/tests/integration/game_setup_flow.test.jsx`: the avatar field is prefilled
      from a stored description, remains editable, and an adventure with no stored description
      starts with an empty field.

**Checkpoint**: User Story 2 is independently complete and testable.

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T024 [P] Run the full quickstart.md backend and frontend command lists and record actual
      pass/fail output for the PR description's Testing section.
- [ ] T025 Manually verify the 320 px viewport case from quickstart.md's *Manual check* section
      with the longest (500-character) description, and note the result in the PR description.

## Dependencies

- Phase 1 (Setup) blocks both Phase 2 (US1) and Phase 3 (US2) — T001 in particular, since neither
  story's description reaches the backend without it.
- Phase 2 (US1) and Phase 3 (US2) have no dependency on each other and may be done in either
  order or interleaved.
- Within Phase 3: T012 → T013 → T015/T017/T019 (model before service before its three call
  sites); T014/T016/T018/T020/T021 depend on their respective implementation task but not on
  each other.
- Phase 4 runs last, after both stories are complete.

## Parallel execution examples

- Setup: T001, T002, T003 touch three different files and can run together.
- Within US1: T004+T005 (backend) can run in parallel with T006+T007 (frontend component);
  T008/T009/T010/T011 depend on T004 and T006 having landed first.
- Within US2: T012 alone, then T013 alone (depends on T012); once T013 lands, T015/T017/T019 and
  their paired tests (T016/T018/T020/T021) can proceed in parallel across their three call sites.

## Implementation strategy

**MVP scope**: User Story 1 alone (Phase 1 + Phase 2) ships a complete, independently valuable
increment — players can see their avatar description mid-session — without touching storage at
all. User Story 2 (Phase 3) adds the remember-and-prefill behavior on top, in either order
relative to US1 per spec.md.
