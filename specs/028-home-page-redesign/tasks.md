---

description: "Task list for the player home page redesign (#328)"
---

# Tasks: Player Home Page Redesign

**Input**: Design documents from `/specs/028-home-page-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Canonical UI**: `specs/designs/07-home-spec.md` (written spec, section numbers below refer
to it) and `specs/designs/07-home.html` (mockup). Both are vendored by T001 and are the
acceptance reference for everything a player sees.

**Tests**: Included — constitution Principle I (Meaningful, Automated Testing) is
NON-NEGOTIABLE in this repo; every behavior change below ships with a test.

**Organization**: Grouped by user story (spec.md) so each is independently implementable and
testable. Task IDs are strictly sequential in execution order; `[P]` marks a task whose
prerequisites are met and which shares no file with another `[P]` task in the same group.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Canonical references & governance

**Purpose**: Get the canonical documents into the repo and make the governing text agree with
them, before any code is written against them. No application code changes in this phase
except the brand rename.

- [X] T001 Vendor both canonical documents from issue #328 into `specs/designs/`: the mockup
  as `07-home.html` and the written design spec as `07-home-spec.md`. In the mockup, delete
  the prototype-only `.statebar` block (the Role / In progress / Available switcher and its
  `<script>` state machine) and repoint internal nav `href`s to the sibling files as
  `02-story-select.html` does. Do not modify `specs/designs/styles.css` — it is already
  byte-identical to the attachment's copy.
- [X] T002 Update `specs/designs/README.md`: add `07-home.html` to the screen-list table, and
  add a "Notes for implementers" entry recording that Home supersedes `02-story-select.html`
  as the acceptance reference for the in-progress/ready-to-play pairing (research.md
  Decision 2) and that Home's Play action enters `06-game-setup.html` at its character-name
  step, skipping that screen's adventure picker (research.md Decision 4).
- [X] T003 Update `.specify/memory/constitution.md` in one edit covering four points:
  (a) the "Adventure select" bullet in **Screen contracts** names `specs/designs/07-home.html`
  as the current acceptance reference, with `02-story-select.html` retained as historical
  prior art; (b) that section's preamble sentence "It holds six screens" becomes seven;
  (c) **Layout and scroll contract** rule 1 is amended to permit page-level scrolling below
  the mobile breakpoint while leaving desktop and tablet bound as before (research.md
  Decision 9); (d) the version and Sync Impact Report are updated per the constitution's own
  Governance section. **Blast-radius file: this edit alone makes `/code-review ultra`
  mandatory before merge, whatever the rest of the diff looks like (CLAUDE.md Code review
  triage).**
- [X] T004 [P] Rename the brand "Lantern" → "LLM Dungeon" (FR-019) in
  `src/frontend/src/components/Layout/NavBar.jsx`,
  `src/frontend/src/components/Layout/TitleBar.jsx` (two occurrences),
  `src/frontend/tests/components/TitleBar.test.jsx`, and in `specs/designs/01-login.html`,
  `02-story-select.html`, `03-play.html`, `04-admin-wizard.html`, `05-admin-users.html`,
  `06-game-setup.html`, `index.html` and `README.md`.

**Checkpoint**: Canonical design reference and governance text are in the repo and agree with
each other; the product name is consistent everywhere it appears.

---

## Phase 2: Foundational — story `blurb` (blocks US1's "Ready to play" row)

**Purpose**: The canonical row (§5.1) shows a blurb that no backend field carries today
(data-model.md). US1 cannot render a correct row until this exists end to end. Nothing else
in the feature depends on it.

- [X] T005 [P] Add `blurb: Optional[str] = None` to the `Story` dataclass in
  `src/backend/models/story.py`, placed with the other optional descriptive fields
  (`tone`, `readingLevel`), and include it in that class's `to_dict`/`from_dict`.
- [X] T006 [P] Add `blurb: Optional[str] = None` to the `StoryDraft` dataclass in
  `src/backend/models/story_draft.py`, placed beside `tone`, and include it in its
  `to_dict`/`from_dict`. Do **not** add it to `is_complete()` — a blurb is not required for
  generation.
- [X] T007 In `src/backend/services/story_draft_service.py`: add `"blurb"` to
  `PATCHABLE_FIELDS`, and carry `blurb` through every draft↔Story conversion in that file
  alongside the existing `coverImageUrl`/`tone` assignments — the draft-seeded-from-story
  path, the save path, and the generation path. Depends on T005, T006.
- [X] T008 [P] Add `blurb` to the story configuration schema in
  `src/backend/services/story_config_file.py` (export and import), defaulting to `None` when
  a file omits it so configurations exported before this field still import (contracts/api.md).
  Depends on T005.
- [X] T009 [P] Add `c.blurb` to the Cosmos projection in `StoryService.list_published_summaries`
  (`src/backend/services/story_service.py`) so `GET /game/adventures` returns it
  (contracts/api.md). Depends on T005.
- [X] T010 Backend tests for the above, in the repo's existing files: blurb patches and
  persists on a draft and survives the draft→Story conversion
  (`src/backend/tests/unit/test_story_draft_service.py`); `list_published_summaries` returns
  it, and a story stored without one returns `None` rather than raising
  (`src/backend/tests/unit/test_story_service.py`); a configuration round-trips with it and
  imports cleanly without it (`src/backend/tests/unit/test_story_config_file.py`).
  Depends on T007, T008, T009.
- [X] T011 Add a "Blurb" `<textarea>` to
  `src/frontend/src/components/Admin/StoryWizard/StepNameCover.jsx` (FR-016), following that
  file's existing `name`/`coverImageUrl` pattern exactly: local state seeded from
  `draft.blurb`, a `useEffect` resync, inclusion in the `dirty` comparison, and in the
  `onPatch({ name, coverImageUrl, blurb })` payload. Depends on T007.
- [X] T012 [P] Cover the wizard field with a test — setting a blurb and saving issues a PATCH
  carrying it — in `src/frontend/tests/integration/admin_story_creation_flow.test.jsx`.
  Depends on T011.

**Checkpoint**: An administrator can author a blurb and the player-facing adventures endpoint
returns it. US1 can now render a complete "Ready to play" row.

---

## Phase 3: User Story 1 — Player lands on Home and sees where they stand (P1) 🎯 MVP

**Goal**: `/menu` renders the canonical Home page: welcome band, both columns, correct states,
correct nav — with real data.

**Independent Test**: Sign in as a player with a mix of sessions and un-started stories and
confirm both lists, the lede copy, and the six states of §6 render correctly with no
navigation beyond sign-in. Play/Resume need not navigate yet (US2 wires them).

### Components (built before the page that composes them)

- [ ] T013 [P] [US1] Create `src/frontend/src/components/Home/Home.css` implementing §2's
  band structure and §7's breakpoints: the `100vh`/`overflow:hidden` shell, the
  `2fr / 1fr` grid (→ `3fr / 2fr` ≤1100px → single column ≤760px), `min-height: 0` on the
  grid and both columns so the inner scrollers work, the 174px row pitch of §5.3, and the
  mobile page-scroll rules (FR-012, FR-013). Every value comes from `specs/designs/styles.css` tokens — no
  literal hex or font names (constitution, UI Design System Requirements).
- [ ] T014 [P] [US1] Create `src/frontend/src/components/Home/WelcomeBand.jsx` per §4: the
  uppercase time-of-day kicker derived from the viewer's own clock (FR-020, e.g. "WEDNESDAY
  AFTERNOON"), a `Welcome back, {firstName}.` heading (first word of the MSAL account's
  display name, matching how `NavBar.jsx` reads `account?.name ?? account?.username`), and
  the lede whose wording is chosen by in-progress count — 0, 1, or n, copy verbatim from §4
  (FR-005).
- [ ] T015 [P] [US1] Create `src/frontend/src/components/Home/StoryRow.jsx` per §5.1 (FR-002) — one
  ready-to-play row: `.card-kicker` reading `{tone} · {sessionLengthMinutes} min` (the
  canonical "genre" is the story's `tone`), the title, the `blurb`, `.card-meta` reading
  `Reading level: {readingLevel}`, and a Play `.btn.btn-secondary` bottom-aligned. The whole
  row is one link; the button is a `<span>` inside it. A `null` blurb renders as no blurb
  line, not the string "null".
- [ ] T016 [P] [US1] Create `src/frontend/src/components/Home/SessionCard.jsx` per §5.2 (FR-003) —
  title clamped to two lines, a meta line reading
  `Chapter {progress.current} · {lastPlayed} · {locationLabel}` (reuse `formatLastPlayed`'s
  behavior from `src/frontend/src/components/GameSetup/SavedGameRow.jsx`), a segmented bar
  filling `progress.current` of `progress.total`, and a Resume `.btn.btn-secondary`. Carry
  the unavailable state `SavedGameRow.jsx` provides today (FR-018): when
  `session.available === false`, mark the card visibly (text, not color alone) and disable
  Resume. Leave a placeholder slot beside Resume for the Delete action — filled in US3
  (T033). A session missing `progress` renders without the chapter and bar rather than
  crashing.
- [ ] T017 [US1] Create `src/frontend/src/components/Home/ReadyToPlayList.jsx` — the column
  head (kicker `START SOMETHING NEW`, heading `Ready to play`) plus the scrolling body of
  `StoryRow`s, with the loading and error states `GameSetup/AdventureList.jsx` already uses.
  Depends on T015.
- [ ] T018 [US1] Create `src/frontend/src/components/Home/InProgressList.jsx` — the column
  head (kicker `KEEP GOING`, heading `In progress`, becoming `Nothing in progress` when the
  list is empty) plus the scrolling body of `SessionCard`s, and §6 state 1's zero-state
  paragraph when there are none. Depends on T016.

### The page, its route, and the nav

- [ ] T019 [US1] Create `src/frontend/src/pages/HomePage.jsx` (FR-001): fetch adventures
  (`listAdventures`) and sessions (`listSavedGames`) from `src/frontend/src/services/gameService.js`,
  derive "ready to play" as published adventures having no session for this player (FR-004),
  pass sessions newest-first to `InProgressList`, compose `WelcomeBand` + both columns, and
  publish refresh through `usePublishRefresh` exactly as `components/Menu/MainMenu.jsx` does
  today so the nav's Refresh button keeps working. Depends on T013, T014, T017, T018.
- [ ] T020 [US1] Add the account states `MainMenu` owns today to `HomePage.jsx` (FR-017):
  `denied` renders `components/Login/AccessDeniedScreen.jsx`; an account with neither
  capability renders the "Access Pending" explanation; and an account holding Administrator
  but not Player sees an in-place explanation instead of empty columns or a raw error
  (spec.md Edge Cases), with the nav's admin destinations left usable. Depends on T019.
- [ ] T021 [US1] Point the `/menu` route at `HomePage` in `src/frontend/src/App.jsx` (FR-001),
  replacing the `MainMenu` import and element. Depends on T019.
- [ ] T022 [US1] Update `src/frontend/src/components/Layout/NavBar.jsx`'s player variant to
  the canonical bar of §3 (FR-011, research.md Decision 7): add "Home" (`to="/menu"`, with
  `aria-current="page"` when there); keep "My stories" as an inert placeholder following the
  `href="#"` + `preventDefault` precedent that file already uses for "Badges"; for
  administrators render "New story" (`/admin/stories/new`), "Users" (`/admin/accounts`) and
  the retained "Admin" (`/admin`, keeping every admin destination reachable — FR-015);
  and suffix the name chip with `· Player` or
  `· Administrator` from `useCapabilities()` (FR-011a). Leave the admin-section variant
  unchanged.
- [ ] T023 [US1] Delete the superseded `src/frontend/src/components/Menu/` files —
  `MainMenu.jsx`, `MainMenu.css`, `GameMenuItem.jsx`, `AdminMenuItem.jsx` — and their tests
  `src/frontend/tests/components/MainMenu.test.jsx` and
  `src/frontend/tests/components/AdminMenuItem.test.jsx`. Depends on T021, T022.

### Tests

- [ ] T024 [P] [US1] Component tests for `HomePage` in
  `src/frontend/tests/components/Home/HomePage.test.jsx`: §6's six states (zero/one/many
  in-progress, one/many ready-to-play, and that a column overflowing scrolls rather than
  growing the page), a story with an active session absent from "Ready to play" (FR-004),
  the lede wording at 0/1/n (FR-005), the denied and no-capability states (FR-017), and the
  unavailable card (FR-018). Depends on T020.
- [ ] T025 [P] [US1] Update the existing tests that assert the retired menu and the old nav:
  `src/frontend/tests/integration/main_menu_refresh.test.jsx`,
  `src/frontend/tests/integration/main_menu_permissions_refresh.test.jsx`,
  `src/frontend/tests/integration/nav_capability_visibility.test.jsx` and
  `src/frontend/tests/components/NavBar.test.jsx` — covering the canonical links, the
  administrator-only links, and the role-suffixed chip (FR-011/FR-011a). Depends on T023.

**Checkpoint**: Home is complete and correct as a landing page. Its Play/Resume controls do
not navigate yet.

---

## Phase 4: User Story 2 — Player resumes or starts a story in one action (P1)

**Goal**: Play and Resume each lead, in one click, to the right place — new character setup,
or the existing session reopened — with no redundant adventure picker.

**Independent Test**: Play on an un-started story opens character-name entry directly; Resume
on a card reopens that exact session at its saved point.

- [ ] T026 [US2] Narrow `src/frontend/src/pages/GamePage.jsx`: stop rendering
  `GameSetup/StoriesInProgress.jsx` and `GameSetup/AdventureList.jsx` and drop the
  `adventures`/`savedGames` state that only fed them. Read `useLocation().state` and accept
  either `{ adventureId }` — begin at `CharacterNameStep` for that adventure — or
  `{ resumeSessionId }` — run the existing `handleResume` for it on mount (research.md
  Decision 10). Keep `handleResume` itself unchanged, including its `isActiveForPlayer`
  skip, its 409 `already_active` tolerance and its story-unavailable messages, and keep
  `resumeError`/`checkpointExitNotice` rendering. Reaching `/game` with no route state sends
  the player back to `/menu`. Depends on T021.
- [ ] T027 [US2] Wire `HomePage`'s Play action to
  `navigate("/game", { state: { adventureId } })` (FR-006). Depends on T019, T026.
- [ ] T028 [US2] Wire `HomePage`'s Resume action to
  `navigate("/game", { state: { resumeSessionId: session.sessionId } })` (FR-007); an
  unavailable session (`available === false`) does not navigate. Depends on T019, T026.
- [ ] T029 [US2] Update `src/frontend/tests/integration/game_setup_flow.test.jsx` and
  `src/frontend/tests/integration/save_and_continue.test.jsx` for the narrowed `GamePage`
  (entered with route state, no in-page adventure grid or in-progress list). Depends on T026.
- [ ] T030 [P] [US2] Add `src/frontend/tests/integration/home_play_resume_flow.test.jsx`:
  Home → Play → character setup → session created; and Home → Resume → that session
  rehydrated without passing through character setup. Depends on T027, T028.

**Checkpoint**: Both P1 stories are done — Home is a complete landing-to-play flow.

---

## Phase 5: User Story 3 — Player deletes a saved session (P2)

**Goal**: A player removes their own saved session behind a confirmation, and the story
returns to "Ready to play".

**Independent Test**: Delete a session from its card, confirm, and watch the card disappear
and the story reappear on the left; another player's session id is refused by the server.

### Backend

- [ ] T031 [P] [US3] Add `delete_player_session(session_id, player_id)` to `PlaySessionService`
  in `src/backend/services/play_session_service.py`: read the item via `_read_item`, raise
  `SessionNotFoundError` when absent, raise `ForbiddenError` when `playerId` does not match
  the caller (FR-010), otherwise `self._container().delete_item(item=session_id, partition_key=session_id)`
  — the same primitive `delete_active_sessions_for_adventure` uses (data-model.md).
- [ ] T032 [US3] Add a `delete_session` handler to `src/backend/api/game/sessions.py`,
  structured like `resume_session` in that file: `authorize_player`, read `sessionId` from
  `req.route_params`, call the service, map `SessionNotFoundError` → 404 `not_found` and
  `ForbiddenError` → `forbidden_access_not_granted()`, and return 200 with
  `{"status": "deleted", "sessionId": …}` per contracts/api.md. Then register
  `DELETE /api/game/sessions/{sessionId}` in `src/backend/function_app.py` beside the
  existing `game/sessions/{sessionId}` routes, wrapped in `_guarded` like its neighbours.
  Depends on T031.
- [ ] T033 [US3] Backend tests: the owner's delete returns 200 and the session no longer
  appears in `list_player_sessions`; a second delete of the same id returns 404; another
  player's session returns 403 — in `src/backend/tests/unit/test_play_session_service.py`
  and `src/backend/tests/integration/test_game_sessions_endpoint.py`. Depends on T032.

### Frontend

- [ ] T034 [P] [US3] Add `deleteSession(token, sessionId)` to
  `src/frontend/src/services/gameService.js`, following that file's existing axios +
  `X-Custom-Authorization` pattern, calling `DELETE /game/sessions/{sessionId}`.
- [ ] T035 [US3] Add `src/frontend/src/hooks/useDeleteSession.js`, mirroring
  `src/frontend/src/hooks/useDeleteStory.js`: `status` (idle|working|error),
  `confirmingDelete`, and `requestDelete`/`confirmDelete`/`cancelDelete`, calling
  `deleteSession` and invoking `onDeleted(sessionId)` on success. A 404 counts as success —
  the session is gone, which is what was asked (contracts/api.md). Depends on T034.
- [ ] T036 [US3] Add `src/frontend/src/components/Home/SessionDeleteAction.jsx`, mirroring
  `src/frontend/src/components/Admin/StoryDeleteAction.jsx`: a Delete `.btn` that
  `preventDefault`/`stopPropagation`s so it never triggers the card's resume link, and the
  design-system dialog (FR-008; `.dialog-backdrop`, `.dialog`, `role="dialog"`,
  `aria-modal="true"`, `aria-labelledby`) carrying the canonical copy verbatim — "Delete your
  saved session for “{title}”? Your progress will be lost." — with a cancel action and a
  confirm action, plus the error message shown when the call fails (research.md Decisions 6
  and 11). Not `window.confirm`. Depends on T035.
- [ ] T037 [US3] Render `SessionDeleteAction` in `SessionCard.jsx`'s placeholder slot
  (T016) and have `HomePage` drop the deleted session from its own state via `onDeleted`,
  which returns that story to "Ready to play" through T019's existing derivation — no
  refetch (FR-009). Depends on T016, T019, T036.
- [ ] T038 [P] [US3] Frontend tests: cancel leaves the card in place; confirm removes it and
  the story reappears in "Ready to play"; deleting the only session falls back to the
  zero state; a failed call surfaces the error and keeps the card — in
  `src/frontend/tests/components/Home/SessionDeleteAction.test.jsx` and
  `src/frontend/tests/integration/home_delete_session_flow.test.jsx`. Depends on T037.

**Checkpoint**: All three user stories complete and independently verified.

---

## Phase 6: Polish & cross-cutting

- [ ] T039 [P] Accessibility pass over the Home components against §8 and the constitution's
  Accessibility section: every control keyboard-operable (FR-014), a visible `:focus-visible` outline
  in the accent color (never the browser default), and no state carried by color alone —
  including the unavailable card of FR-018.
- [ ] T040 [P] Responsive check at 1100px, 760px and 320px per §7 and quickstart.md scenario
  6: no horizontal page scroll at any width, both columns reachable, and Play/Resume/Delete
  at least 44px tall on mobile (FR-013).
- [ ] T041 Run the full suites and fix regressions from the `MainMenu`/`GamePage` removals
  and the brand rename: `pytest` for the backend and `npm --prefix src/frontend test` for
  the frontend, both inside the devcontainer. Depends on every preceding task.
- [ ] T042 Confirm the PR description records the three deliberate departures from the
  canonical mockup — the design-system delete dialog (Decision 6), the retained "Admin" nav
  link (Decision 7) and the mobile scroll amendment (Decision 9) — and names
  `/code-review ultra` as the required tier, because `.specify/memory/constitution.md` is in
  the diff. Depends on T041.

---

## Dependencies & Execution Order

Phases run in order; within a phase, task IDs are already in execution order and each task
names what it depends on.

- **Phase 1** is independent of all code work (T004 is parallel to everything).
- **Phase 2** blocks US1 only through the blurb rendered by `StoryRow` (T015).
- **US1 (Phase 3)** depends on Phase 2; it is the MVP.
- **US2 (Phase 4)** depends on US1's page and route existing (T019, T021).
- **US3 (Phase 5)** depends on US1's `SessionCard`/`HomePage` (T016, T019). Its backend half
  (T031–T033) shares no file with US2 and can run alongside Phase 4.
- **Phase 6** runs last.

## Parallel Execution Examples

```
T004                          ‖ all of Phase 1 (rename shares no file with T001–T003)
T005, T006                    ‖ (different model files)
T008, T009                    ‖ (different services; both need T005)
T013, T014, T015, T016        ‖ (four new component files)
T024, T025                    ‖ (different test files)
T031–T033 (backend delete)    ‖ Phase 4 (no shared files)
T039, T040                    ‖ (review passes over different concerns)
```

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + US1 (T001–T025)**: a complete, correct Home page with real data.
**US2 (T026–T030)** makes it navigable end to end; both P1 stories together are the minimum
shippable redesign. **US3 (T031–T038)** is the P2 increment and can land in the same PR or a
fast follow — nothing in US1 or US2 depends on it.
