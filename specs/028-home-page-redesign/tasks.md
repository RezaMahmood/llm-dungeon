---

description: "Task list for the player home page redesign (#328)"
---

# Tasks: Player Home Page Redesign

**Input**: Design documents from `/specs/028-home-page-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included — constitution Principle I (Meaningful, Automated Testing) is
NON-NEGOTIABLE in this repo; every behavior change below ships with a test.

**Organization**: Grouped by user story (spec.md) so each is independently implementable
and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3, matching spec.md's priorities (US1, US2 = P1; US3 = P2)

## Phase 1: Setup (design reference & governance docs)

**Purpose**: Vendor the new design reference and bring the constitution's screen-contract
text in line with it, before any code changes reference it.

- [ ] T001 Copy the issue's mockup to `specs/designs/07-home.html`, adjusting only its
  internal nav `href`s to match the existing five files' conventions (see
  `specs/designs/02-story-select.html` for the pattern); leave `specs/designs/styles.css`
  untouched (already byte-identical to the attachment's copy).
- [ ] T002 Update `specs/designs/README.md`: add `07-home.html` to the screen list table and
  add an implementer note under "Notes for implementers" describing Home's relationship to
  `02-story-select.html` (superseded acceptance reference — see research.md Decision 2) and
  to `06-game-setup.html` (Home's Play action now leads directly into 06's character-name
  step, skipping its own adventure-picker step — see research.md Decision 4).
- [ ] T003 Update `.specify/memory/constitution.md`'s "Adventure select" screen-contract
  bullet (Screen contracts section) to name `specs/designs/07-home.html` as the current
  acceptance reference, keep `02-story-select.html` referenced only as historical prior art,
  and bump the constitution's version/Sync Impact Report per its own governance section
  (a wording/reference change, not a principle change). **This file is `.specify/memory/` —
  editing it is a blast-radius item requiring `/code-review ultra` before merge regardless
  of the rest of this diff's size (CLAUDE.md Code review triage).**

**Checkpoint**: Design reference and governance text match the target behavior; no code
changed yet.

---

## Phase 2: Foundational — none

No infrastructure is shared by all three user stories beyond Phase 1's documentation, so
there is no blocking Phase 2. Proceed directly to User Story 1.

---

## Phase 3: User Story 1 - Player lands on Home and sees where they stand (Priority: P1) 🎯 MVP

**Goal**: A signed-in player sees, on one screen with no further clicks, a welcome band and
both the "Ready to play" and "In progress" lists per spec.md's data contract — including the
new `blurb` field the design requires and today's `Story` model lacks.

**Independent Test**: Sign in as a player with a mix of sessions and un-started stories;
`/menu` renders `HomePage` showing correct welcome copy, both lists, and (per quickstart.md
scenario 5) the two extra admin nav links only for an administrator account.

### Backend: `blurb` field (research.md Decision 5)

- [ ] T004 [P] [US1] Add `blurb: Optional[str] = None` to `Story` in
  `src/backend/models/story.py` (alongside `tone`/`readingLevel`; include in `to_dict`/
  `from_dict`).
- [ ] T005 [P] [US1] Add `blurb: Optional[str] = None` to `StoryDraft` in
  `src/backend/models/story_draft.py` (same placement pattern as `tone`).
- [ ] T006 [US1] Add `"blurb"` to `PATCHABLE_FIELDS` in
  `src/backend/services/story_draft_service.py`, and thread `blurb=draft.blurb` /
  `blurb=story.blurb` through the draft↔Story conversions already carrying `coverImageUrl`/
  `worldPrompt` in that file (draft-from-story and story-from-draft/generation paths).
- [ ] T007 [US1] Add `blurb` to the exported/imported configuration schema in
  `src/backend/services/story_config_file.py`, defaulting to `None` when absent from an
  older exported file (never a validation failure — contracts/api.md).
- [ ] T008 [US1] Add `c.blurb` to the Cosmos projection in
  `StoryService.list_published_summaries` (`src/backend/services/story_service.py`) so
  `GET /game/adventures` returns it (contracts/api.md).
- [ ] T009 [P] [US1] Backend tests: draft PATCH accepts/persists `blurb`, publish carries it
  to the `Story`, and `list_published_summaries` returns it — extend
  `src/backend/tests/services/test_story_draft_service.py` and
  `src/backend/tests/services/test_story_service.py`.

### Frontend: authoring the blurb

- [ ] T010 [US1] Add a "Blurb" textarea to
  `src/frontend/src/components/Admin/StoryWizard/StepNameCover.jsx`, following the exact
  `name`/`coverImageUrl` state/dirty/save pattern already in that file.
- [ ] T011 [P] [US1] Update `src/frontend/tests/integration/admin_story_creation_flow.test.jsx`
  (or add a focused component test) to cover setting and saving the blurb field.

### Frontend: the Home page itself

- [ ] T012 [P] [US1] Create `src/frontend/src/components/Home/WelcomeBand.jsx` — kicker,
  "Welcome back, {firstName}." heading, and the zero/one/many lede copy from spec.md §4/FR-005.
- [ ] T013 [P] [US1] Create `src/frontend/src/components/Home/StoryRow.jsx` — one "Ready to
  play" row (kicker `{tone} · {sessionLengthMinutes} min`, title, `blurb`,
  `Reading level: {readingLevel}`, a Play `.btn.btn-secondary`), per spec.md §5.1.
- [ ] T014 [P] [US1] Create `src/frontend/src/components/Home/ReadyToPlayList.jsx` — maps
  adventures (excluding any with an active session — FR-004) to `StoryRow`s, with the
  loading/error states matching the existing `AdventureList.jsx` pattern.
- [ ] T015 [P] [US1] Create `src/frontend/src/components/Home/SessionCard.jsx` — one
  "In progress" card per spec.md §5.2 (title clamp, meta line, segmented progress bar via
  the same `completed`/`total` derivation `SavedGameRow.jsx` already uses, a Resume
  `.btn.btn-secondary`); render a disabled/placeholder Delete affordance for now — wired up
  in US3 (T032).
- [ ] T016 [P] [US1] Create `src/frontend/src/components/Home/InProgressList.jsx` — maps
  sessions to `SessionCard`s, with the FR-005/spec.md §6 state-1 zero-state message when
  empty.
- [ ] T017 [US1] Create `src/frontend/src/components/Home/Home.css` implementing the
  fixed-viewport/two-independent-scrollers layout and the desktop/tablet/mobile breakpoints
  from spec.md §7, built only from `specs/designs/styles.css` tokens (constitution "UI
  Design System Requirements" — no literal hex/font values).
- [ ] T018 [US1] Create `src/frontend/src/pages/HomePage.jsx`: fetches adventures
  (`listAdventures`) and sessions (`listSavedGames`) via `gameService.js`, derives the
  ready-to-play/in-progress split (FR-004), renders `WelcomeBand` + the two column
  components, and publishes its own refresh via `usePublishRefresh` exactly as `MainMenu`
  does today.
- [ ] T019 [US1] Point the `/menu` route at `HomePage` in `src/frontend/src/App.jsx`
  (replacing the `MainMenu` import/element).
- [ ] T020 [US1] Update `src/frontend/src/components/Layout/NavBar.jsx`'s player nav: add a
  "Home" link (`to="/menu"`, current page) alongside the existing "My stories"/"Badges"
  links, per spec.md §3 — decide alongside T020 whether "My stories" still needs its own
  destination or should be dropped now that Home absorbs its content (research.md Decision
  1); if dropped, remove the dead link rather than pointing it at a page that no longer
  exists.
- [ ] T021 [P] [US1] Remove the now-superseded `src/frontend/src/components/Menu/MainMenu.jsx`,
  `MainMenu.css`, `GameMenuItem.jsx`, `AdminMenuItem.jsx` and their tests
  (`tests/components/MainMenu.test.jsx`, `tests/components/AdminMenuItem.test.jsx`, any
  `GameMenuItem` test), replacing coverage with the new Home component tests below.
- [ ] T022 [P] [US1] Component tests for `HomePage` covering spec.md §6's six states (zero/
  one/many in-progress, one/many ready-to-play, overflow scrolling) and the admin-vs-player
  nav/name-chip difference (FR-011), in `src/frontend/tests/components/Home/HomePage.test.jsx`.

**Checkpoint**: `/menu` shows the full Home page with real data and correct states; User
Story 1 is independently demonstrable (Play/Resume links can 404 until US2 lands, but the
page itself is complete and testable per its own acceptance scenarios).

---

## Phase 4: User Story 2 - Player resumes or starts a story in one action (Priority: P1)

**Goal**: Clicking Play or Resume from Home leads directly into the right flow — a new
session's character setup, or an existing session reopened — with no redundant
adventure-picker step.

**Independent Test**: From Home, Play on an un-started story opens character-name entry
directly (no card-grid re-pick); Resume on a card reopens that exact session.

- [ ] T023 [US2] Narrow `src/frontend/src/pages/GamePage.jsx`: remove its own
  `StoriesInProgress`/`AdventureList` rendering and the `savedGames`/`adventures` state that
  only fed them; accept a pre-chosen `adventureId` (via `useLocation().state`, navigated from
  Home) and render `CharacterNameStep` as the first visible step instead of an
  adventure-picker grid.
- [ ] T024 [US2] Wire `StoryRow`'s Play action (from T013/`ReadyToPlayList`) to
  `navigate("/game", { state: { adventureId } })` in `HomePage.jsx`.
- [ ] T025 [US2] Wire `SessionCard`'s Resume action to call the existing `resumeSession`
  service call and navigate into the play surface exactly as `SavedGameRow.jsx` does today,
  reusing that logic rather than re-deriving it.
- [ ] T026 [P] [US2] Update `src/frontend/tests/integration/game_setup_flow.test.jsx` (and
  any other test asserting the old in-`GamePage` adventure grid) to reflect the narrowed
  flow; add a new `src/frontend/tests/integration/home_play_resume_flow.test.jsx` covering
  Home→Play→setup→session-start and Home→Resume→session-reopen end to end.

**Checkpoint**: Both P1 stories are complete — Home is a fully working landing-to-play flow.

---

## Phase 5: User Story 3 - Player deletes a saved session (Priority: P2)

**Goal**: A player can permanently remove their own saved session from "In progress" behind
a confirmation, and the underlying story reappears in "Ready to play".

**Independent Test**: Delete a session from a card; confirm the card disappears, the story
reappears in "Ready to play", and a second player's session is unaffected. Attempting to
delete another player's session id directly (bypassing the UI) is refused server-side.

### Backend

- [ ] T027 [P] [US3] Add `delete_player_session(session_id, player_id)` to
  `PlaySessionService` in `src/backend/services/play_session_service.py`, following
  `delete_active_sessions_for_adventure`'s delete primitive: read the item, raise
  `SessionNotFoundError` if absent, raise `ForbiddenError` if `playerId` doesn't match, else
  `container().delete_item(...)` (data-model.md).
- [ ] T028 [US3] Add a `delete_session` handler to `src/backend/api/game/sessions.py`
  (mirrors `resume_session`'s structure: `authorize_player`, call the service, map
  `SessionNotFoundError`→404, `ForbiddenError`→`forbidden_access_not_granted()`, success→204
  empty body) per contracts/api.md.
- [ ] T029 [US3] Register `DELETE /api/game/sessions/{sessionId}` in
  `src/backend/function_app.py`, alongside the existing `game/sessions/{sessionId}` routes.
- [ ] T030 [P] [US3] Backend tests: owner delete → 204 and the session is gone from
  `list_player_sessions`; another player's session → 403; missing id → 404 — in
  `src/backend/tests/services/test_play_session_service.py` and
  `src/backend/tests/api/game/test_sessions.py`.

### Frontend

- [ ] T031 [US3] Add `deleteSession(token, sessionId)` to
  `src/frontend/src/services/gameService.js`, following the existing call pattern (axios +
  `X-Custom-Authorization` header).
- [ ] T032 [US3] Wire `SessionCard.jsx`'s Delete control (replacing T015's placeholder):
  `preventDefault`/`stopPropagation`, `window.confirm('Delete your saved session for
  "{title}"? Your progress will be lost.')` per spec.md §5.2, then call `deleteSession` and
  have `HomePage`/`InProgressList` remove the card and let the story reappear in
  "Ready to play" (re-deriving from the already-fetched adventures list, or a lightweight
  refetch — implementer's choice, either satisfies FR-009).
- [ ] T033 [P] [US3] Tests: confirm/cancel behavior, card removal, zero-state fallback when
  the deleted session was the only one, and the story reappearing in "Ready to play" — in
  `src/frontend/tests/components/Home/SessionCard.test.jsx` and a new
  `src/frontend/tests/integration/home_delete_session_flow.test.jsx`.

**Checkpoint**: All three user stories complete and independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T034 [P] Accessibility pass over `Home.css`/the new components: keyboard operability,
  visible focus indicators, no color-only state (constitution "Accessibility"); verify
  against spec.md §8's hover/focus rules.
- [ ] T035 [P] Responsive QA at 320px/760px/1100px per spec.md §7 and quickstart.md scenario 6.
- [ ] T036 Run the full backend and frontend suites and fix any regressions surfaced by the
  `MainMenu`/`GamePage` removals (`pytest`, `npm --prefix src/frontend test`).

## Dependencies & Execution Order

- **Phase 1 (Setup)** has no code dependency but should land first so the design reference
  exists before anyone builds against it.
- **User Story 1 (Phase 3)** depends only on Phase 1. It is the MVP: Home is fully visible
  and correct, even though Play/Resume aren't wired to real navigation yet.
- **User Story 2 (Phase 4)** depends on US1's `HomePage`/`StoryRow`/`SessionCard` existing
  (it wires their actions) — cannot start first.
- **User Story 3 (Phase 5)** depends on US1's `SessionCard` existing (it fills in the Delete
  slot T015 left as a placeholder) but is otherwise independent of US2 — the backend tasks
  (T027–T030) have no frontend dependency and could be built in parallel with Phase 4.
- **Phase 6** runs last.

## Parallel Execution Examples

Within US1, once T004/T005 (model fields) land, T006–T011 (backend plumbing + wizard UI) and
T012–T016 (the five new Home components) can proceed in parallel — different files, no
shared state. Example:

```
T004, T005            → in parallel (different files)
T012, T013, T014,
T015, T016             → in parallel (different components)
T009, T011, T022       → in parallel (different test files)
```

Within US3, T027 (service) and T031 (frontend service call) touch unrelated files and can
proceed in parallel; T028/T029 depend on T027, T032 depends on T031 and on US1's T015.

## Implementation Strategy

**MVP = User Story 1** (Phase 1 + Phase 3): ships a fully correct, read-only Home page.
Add **User Story 2** next to make it navigable end-to-end (both P1s together are the
minimum shippable redesign). **User Story 3** (Delete) is the incremental P2 that can follow
in the same PR or a fast-follow — nothing in US1/US2 depends on it.
