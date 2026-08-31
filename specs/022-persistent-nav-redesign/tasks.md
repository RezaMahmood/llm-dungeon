---

description: "Task list for Persistent Navigation & Design Refresh"
---

# Tasks: Persistent Navigation & Design Refresh

**Input**: Design documents from `/specs/022-persistent-nav-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/nav-bar.md, contracts/screen-restyle.md, quickstart.md

**Tests**: Included — Constitution Principle I (NON-NEGOTIABLE) requires automated tests for every functionality/edge case; this feature's plan.md Constitution Check commits to component/integration tests for `NavBar`, `TitleBar`, `AuthenticatedLayout`, and regression coverage of unchanged behavior on `AdminAccountsPage`/`AdminStoryWizardPage`.

**Organization**: Tasks are grouped by user story per spec.md's priorities (P1–P3, plus the design-consistency P2 story). All frontend paths are relative to `src/frontend/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec.md's US1–US4
- File paths are exact and relative to `src/frontend/` unless stated otherwise

---

## Phase 0: UI Design Sign-Off Gate (Constitution Principle XI — BLOCKING)

**Purpose**: Resolve the Refresh-control discrepancy documented in plan.md's Constitution Check and research.md §6 before any nav-bar implementation task begins. Per Principle XI, this is a design-time human gate, not a task the implementing agent can satisfy on its own judgment.

- [X] T001 **RESOLVED 2026-08-31 — product owner decision: "Refresh is part of another spec - add placeholder."** This feature ships no Refresh button; `NavBar`'s trailing cluster is a flex row with an explicit placeholder mount point for 019's future `RefreshButton`. Design mockups are left unchanged; 019's own docs need correcting when that feature resumes. Recorded in `plan.md`'s Constitution Check (Principle XI). Original task text: Present the Refresh-slot discrepancy to the requesting user/product owner: `specs/designs/02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`, and `README.md` currently show **no** Refresh control in the shared nav bar (only `03-play.html`'s title bar has one), contradicting `019-spa-refresh-button`'s planning docs. Obtain an explicit decision: **(a)** product owner updates the four design files to add the Refresh control to the nav bar, making 019's docs accurate, or **(b)** product owner confirms no Refresh control belongs in the nav bar for `02`/`04`/`05` (title bar only), and 019's task docs get corrected instead. Record the decision and date in `specs/022-persistent-nav-redesign/plan.md`'s Constitution Check (Principle XI section) and in `specs/019-spa-refresh-button/plan.md` if outcome (b) is chosen or 019's docs need correcting. **This task is not complete until the product owner has confirmed the decision — not merely until it is written down.**

**Checkpoint**: Principle XI gate satisfied. Nav-bar implementation tasks (Phase 3+) may now proceed with a settled trailing-button-cluster contract.

---

## Phase 1: Setup

**Purpose**: No new dependencies or project scaffolding are required (plan.md Technical Context: all dependencies existing). This phase only confirms the working baseline.

- [X] T002 Run `npm test` and `npm run lint` (or equivalent) in `src/frontend/` to confirm a clean baseline before any change in this feature; record the passing baseline test count for later comparison.

**Checkpoint**: Baseline confirmed green.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared layout components every user story's screens mount into. No user-story phase below can be implemented until this phase is complete.

**⚠️ CRITICAL**: Depends on Phase 0 (T001) being resolved, since `NavBar`'s trailing button cluster markup depends on that decision.

- [X] T003 [P] Create `AuthenticatedLayout.jsx` in `src/frontend/src/components/Layout/AuthenticatedLayout.jsx` per `contracts/nav-bar.md`: reads `useLocation().pathname` via `react-router-dom`, renders `NavBar` for every authenticated route except `/game`, renders `TitleBar` on `/game`, renders `children` below/after the chosen header (FR-001, FR-006, data-model.md's render-mode table).
- [X] T004 [P] Create `NavBar.jsx` in `src/frontend/src/components/Layout/NavBar.jsx` per `contracts/nav-bar.md`'s markup base and `data-model.md`'s `NavItem` derivation table: reads `hasPlayer`/`hasAdministrator` from `useCapabilities()`, derives the admin link set (Stories `/admin`, New story `/admin/stories/new`, People `/admin/accounts`), the player link set (My stories `/menu`, Badges), the dual-capability cross-role links (Player view, Admin), sets `aria-current="page"` on the item matching `useLocation().pathname`, and always renders "Sign out" plus the user's display name right-aligned as an ordinary flex row (per T001's resolved trailing-cluster contract) (FR-002, FR-003, FR-004, FR-007, FR-008, FR-009).
- [X] T005 [P] Create `TitleBar.jsx` in `src/frontend/src/components/Layout/TitleBar.jsx` per `contracts/nav-bar.md`'s markup base (`specs/designs/03-play.html:23-33`, Refresh button excluded — 019's scope): brand mark linking to `/menu`, truncating story title, "Save a checkpoint" and "Pause & exit" buttons wired to placeholder/no-op handlers matching `GamePage.jsx`'s current placeholder status (FR-006).
- [X] T006 [P] Add any narrowly-scoped layout utility classes needed by `NavBar`/`TitleBar` (e.g. text-overflow ellipsis truncation, `.nav-divider`) to `src/frontend/src/styles/designTokens.css`, reusing existing tokens only — no new hex/magic-pixel values (Principle VIII, contracts/nav-bar.md item 6).
- [X] T007 [P] Component test: `NavBar` renders the correct link set, cross-role links, and `aria-current` for each of the four capability combinations (player-only, admin-only, dual, neither) in `src/frontend/tests/components/NavBar.test.jsx`, per data-model.md's derivation table.
- [X] T008 [P] Component test: `TitleBar` renders only its compact header content and never primary nav links, with story-title truncation, in `src/frontend/tests/components/TitleBar.test.jsx`; assert `TitleBar` itself introduces no extra height/padding beyond what `03-play.html`'s compact header specifies, so the story pane below it loses no reading area (SC-006).
- [X] T009 [P] Component test: `AuthenticatedLayout` renders `NavBar` on non-`/game` authenticated routes and `TitleBar` on `/game`, in `src/frontend/tests/components/AuthenticatedLayout.test.jsx`.
- [X] T010 Modify `ProtectedRoute.jsx` (`src/frontend/src/components/Auth/ProtectedRoute.jsx`) to wrap its authenticated `children` in `<AuthenticatedLayout>`, without changing its existing authentication/capability-gate logic (FR-001, FR-009; coordinate with 019-spa-refresh-button's separate MSAL-timing change to this same file per plan.md's Cross-Feature Dependencies section — additive, non-conflicting).

**Checkpoint**: `AuthenticatedLayout`/`NavBar`/`TitleBar` exist, are tested in isolation, and are mounted for every guarded route. User-story phases below now restyle individual screens on top of this foundation.

---

## Phase 3: User Story 1 - Navigate away from an in-progress story without losing it (Priority: P1) 🎯 MVP

**Goal**: An administrator can leave the story-creation wizard mid-edit via the nav bar and return with saved progress intact.

**Independent Test**: Start a new story in the wizard, fill in at least one step, click "People" in the nav bar, then click back into "New story" — previously saved wizard content is still present, and no browser back-button or hub-menu navigation was required.

### Tests for User Story 1

- [X] T011 [P] [US1] Integration test in `src/frontend/tests/integration/wizard_nav_persistence.test.jsx`: start the wizard, save step 1 content, click a different nav item, click back into "New story," assert the saved fields are still populated (FR-005, SC-003).
- [X] T012 [P] [US1] Integration test in `src/frontend/tests/integration/admin_story_creation_flow.test.jsx` (extend existing): assert the nav bar is present and identical (same items, same position) on the wizard and on the screen navigated to, per spec Acceptance Scenario 3.

### Implementation for User Story 1

- [X] T013 [US1] Modify `AdminStoryWizardPage.jsx` (`src/frontend/src/pages/AdminStoryWizardPage.jsx`): remove any ad hoc page-level header now superseded by `NavBar`; restyle the step-tab row and step content per `04-admin-wizard.html` (contracts/screen-restyle.md); leave `activeStep` state, draft fetch/save/autosave logic, and per-step validation entirely unchanged (FR-005, FR-012).
- [X] T014 [US1] Verify (no code change expected) that routing away from `/admin/stories/new` and back re-fetches the draft via the existing draft-fetch-on-mount behavior, satisfying FR-005/SC-003 per research.md's decision — add a regression assertion to T011's test if any gap is found.

**Checkpoint**: User Story 1 is independently functional and testable — wizard progress survives nav-bar navigation.

---

## Phase 4: User Story 2 - One consistent look across the app (Priority: P2)

**Goal**: All five primary screens share one coherent visual design from the Modernist reference system, and the admin "Stories" nav destination shows a real (if minimal) stories list rather than an unrelated placeholder (FR-013).

**Independent Test**: Visit sign-in, story select, story play, admin wizard, and People in turn; confirm each uses the shared color palette, typography, and component styling from the reference designs with no screen left in old styling. Separately, click "Stories" in the admin nav and confirm it shows existing stories (or an empty state), visibly distinct from "New story."

### Tests for User Story 2

- [X] T015 [P] [US2] Component test in `src/frontend/tests/components/LoginScreen.test.jsx` (extend existing): assert `LoginScreen.jsx` uses only design-token classes (`.btn`, `.hr`, `.text-muted`) matching `01-login.html`, with no persistent nav bar rendered (FR-009).
- [X] T016 [P] [US2] Component test in `src/frontend/tests/components/MainMenu.test.jsx` (extend existing): assert `MainMenu.jsx` renders under `NavBar` with its ad hoc header/logout button removed, matching `02-story-select.html`'s layout, while `GameMenuItem`/`AdminMenuItem` logic is unchanged.
- [X] T017 [P] [US2] Integration test in `src/frontend/tests/integration/admin_accounts.test.jsx` (extend existing): assert `AdminAccountsPage.jsx` renders the add-account form and account list per `05-admin-users.html`'s layout, with all existing data-fetch/mutation assertions still passing (FR-011, FR-012).
- [X] T017a [P] [US2] Integration test in `src/frontend/tests/integration/admin_stories_list.test.jsx` (new): mock `storyService.js`'s `listStories`, assert `AdminPage.jsx` renders each returned story's name and published/draft status; assert an empty-state message (no error) renders when the list is empty (FR-013, SC-007).

### Implementation for User Story 2

- [X] T018 [P] [US2] Confirm/complete `LoginScreen.jsx` (`src/frontend/src/components/Login/LoginScreen.jsx`) alignment with `01-login.html`; remove `LoginScreen.css` rules now superseded by token classes if any remain (research.md: largely already token-based).
- [X] T019 [US2] Modify `MainMenu.jsx` (`src/frontend/src/components/Menu/MainMenu.jsx`): remove the ad hoc `<h1>`/logout header (now provided by `NavBar` via `AuthenticatedLayout`), restyle remaining body content per `02-story-select.html`'s design language; retire `src/frontend/src/components/Menu/MainMenu.css` in favor of `designTokens.css` classes, deleting the file once no rules remain in use.
- [X] T020 [US2] Modify `AdminAccountsPage.jsx` (`src/frontend/src/pages/AdminAccountsPage.jsx`): restyle the add-account form and account list layout per `05-admin-users.html`, keeping `AccountForm`/`AccountList` components and their one-at-a-time remove-with-confirmation behavior functionally unchanged (FR-011, FR-012).
- [X] T020a [P] [US2] ~~Create `storyService.js`~~ **Superseded during implementation**: `src/frontend/src/services/storyDraftService.js` already exports a `listStories(token)` calling `GET /manage/stories` (and `getStory`), so creating a second service would have been a parallel reimplementation of an existing one (Principle VIII: no duplicate of something the codebase already provides; Principle IV/YAGNI). `AdminPage.jsx` imports the existing `listStories` instead. No new file created.
- [X] T021 [US2] Modify `AdminPage.jsx` (`src/frontend/src/pages/AdminPage.jsx`): fetch stories on mount via `storyService.js`'s `listStories` (same `useCallback`/`useEffect`/token-acquisition pattern as `AdminAccountsPage.jsx`'s `refresh()`), render each story's name and a published/draft status tag using existing token-based list/tag styling, and render an explicit empty-state message when the list is empty; this is the "Stories" nav destination, distinct from "New story" (FR-002, FR-013, SC-007). No dedicated mockup exists for this screen — restyle is token-based, not tied to a specific `specs/designs/*.html` file. Read-only: no create/edit/publish/delete action is added here (005-story-publishing/012-story-editing-and-review's scope).
- [X] T022 [US2] Modify `GamePage.jsx` (`src/frontend/src/pages/GamePage.jsx`): render under `TitleBar` (via `AuthenticatedLayout`) instead of any prior header; body content remains the existing placeholder pending `008-core-gameplay` (FR-006).

**Checkpoint**: All five primary screens (plus the admin hub placeholder) render on the shared design-token system with no functional regressions.

---

## Phase 5: User Story 3 - See only the destinations you're allowed to use (Priority: P2)

**Goal**: Nav items visible to a user exactly match their granted capabilities, with cross-role links for dual-capability accounts.

**Independent Test**: Sign in as a player-only account and confirm no admin links appear; sign in as a dual-capability account and confirm "Player view"/"Admin" cross-links both work.

### Tests for User Story 3

- [X] T023 [P] [US3] Integration test in `src/frontend/tests/integration/admin_signin_flow.test.jsx` (extend existing) or a new `src/frontend/tests/integration/nav_capability_visibility.test.jsx`: for each of player-only, admin-only, dual, and neither capability combinations, assert the exact nav item set rendered matches data-model.md's derivation table (FR-002, FR-003, FR-008, spec Acceptance Scenarios 1–3).
- [X] T024 [P] [US3] Integration test: dual-capability account clicking "Player view" from the admin nav lands on `/menu` and shows an "Admin" link back, in the same test file as T023.

### Implementation for User Story 3

- [X] T025 [US3] Verify (no new logic expected — `NavBar` from T004 already implements this) that `NavBar`'s capability-derived visibility exactly matches FR-002/003/008 for all four combinations; fix any discrepancy found by T023/T024 directly in `NavBar.jsx`.

**Checkpoint**: Capability-driven nav visibility is verified correct for every account type, including cross-role navigation.

---

## Phase 6: User Story 4 - Always know where you are (Priority: P3)

**Goal**: Exactly one nav item is visually marked current, matching the screen being viewed.

**Independent Test**: Load each primary screen in turn and confirm exactly one nav item carries active styling/`aria-current`.

### Tests for User Story 4

- [X] T026 [P] [US4] Component test (extend `src/frontend/tests/components/NavBar.test.jsx` from T007): for each route (`/menu`, `/admin`, `/admin/stories/new`, `/admin/accounts`), assert exactly one nav item has `aria-current="page"` and the active-styling class, matching spec Acceptance Scenarios 1–2 (FR-007).

### Implementation for User Story 4

- [X] T027 [US4] Verify (no new logic expected — T004/T009 already implement route-matching) that `aria-current` and active styling are correctly applied on every route; fix any discrepancy found by T026 directly in `NavBar.jsx`/`AuthenticatedLayout.jsx`.

**Checkpoint**: All four user stories are independently functional and verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final regression pass, quickstart validation, and the constitution-mandated user-verified acceptance gate.

- [X] T028 [P] Run the full `src/frontend/` Vitest suite and confirm all pre-existing tests for `MainMenu`, `AdminAccountsPage`, `AdminStoryWizardPage`, `LoginScreen`, and capability/auth scenarios (`tests/e2e/denial_scenarios.test.jsx`, `tests/scenarios/unauthorized_user.test.jsx`, `tests/hooks/useCapabilities.test.jsx`) still pass, with only rendering assertions changed (FR-012), and that the new `admin_stories_list.test.jsx` (T017a) passes.
- [X] T029 Run `quickstart.md`'s manual validation scenarios 1–7 locally (`npm run dev` in `src/frontend/`) across player-only, admin-only, dual-capability, and no-capability test accounts, including scenario 1 (admin "Stories" list vs. "New story").
- [X] T030 **Final acceptance (Constitution Principle IX, NON-NEGOTIABLE)**: the requesting user/product owner — not the implementing agent — exercises scenarios 1–7 from `quickstart.md` against the real deployed environment (or the most representative environment available), including explicit confirmation of the Principle XI Refresh-slot outcome recorded in T001 and of the FR-013 admin stories list, and confirms the feature behaves as intended end-to-end. This task is not complete until that confirmation is given.

  **Approved 2026-08-31** against the deployed environment
  (`https://calm-bay-063862603.7.azurestaticapps.net/`), Gates 0–8, by the
  requesting user. **Gate 7 initially failed**: on `/game`, "Pause & exit" had
  no handler wired at all (`AuthenticatedLayout` rendered `<TitleBar />` with
  no props) and did not return the player to story select. Fixed:
  `TitleBar.jsx` now defaults `onPauseExit` to `navigate("/menu")` when the
  page supplies no handler of its own, so the button is never a dead end
  while `008-core-gameplay` still owns the real pause/checkpoint behavior.
  Covered by a new test in `tests/components/TitleBar.test.jsx`. Re-verified
  and approved after the fix.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Sign-off gate)**: No dependencies — do first. BLOCKS Phase 2's `NavBar` trailing-cluster implementation (T004).
- **Phase 1 (Setup)**: No dependencies — can run in parallel with Phase 0.
- **Phase 2 (Foundational)**: Depends on Phase 0 (T001) and Phase 1 (T002). BLOCKS all user-story phases.
- **Phase 3 (US1, P1 — MVP)**: Depends on Phase 2 completion.
- **Phase 4 (US2, P2)**: Depends on Phase 2 completion. Independent of Phase 3, but recommended after it since both touch `AdminStoryWizardPage.jsx`'s surrounding markup (T013 vs T019/T020 are different files, no actual conflict).
- **Phase 5 (US3, P2)**: Depends on Phase 2 completion (NavBar's capability logic already built in T004); mostly verification.
- **Phase 6 (US4, P3)**: Depends on Phase 2 completion (aria-current logic already built in T004); mostly verification.
- **Phase 7 (Polish)**: Depends on all desired user-story phases being complete; T030 is the closing task for the entire feature.

### Parallel Opportunities

- T003, T004, T005, T006 (different new files) can be built in parallel once Phase 0/1 are done.
- T007, T008, T009 (test files) can be written in parallel with each other and alongside T003–T006 (test-first, if following TDD) or immediately after.
- T015, T016, T017, T017a (independent test files across different screens) can run in parallel.
- T018 (Login) and T020a (`storyService.js`, a new independent file) are independent of T019/T020/T021/T022 and of each other, and can run in parallel with all of them. T021 depends on T020a (needs `listStories` to exist first).
- T023/T024 and T026 can run in parallel with each other and with Phase 4's tasks, since all depend only on Phase 2's completed `NavBar`.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After Phase 0/1 complete, launch the four new component files together:
Task: "Create AuthenticatedLayout.jsx in src/frontend/src/components/Layout/AuthenticatedLayout.jsx"
Task: "Create NavBar.jsx in src/frontend/src/components/Layout/NavBar.jsx"
Task: "Create TitleBar.jsx in src/frontend/src/components/Layout/TitleBar.jsx"
Task: "Add layout utility classes to src/frontend/src/styles/designTokens.css"

# Then their component tests in parallel:
Task: "Component test for NavBar in src/frontend/tests/components/NavBar.test.jsx"
Task: "Component test for TitleBar in src/frontend/tests/components/TitleBar.test.jsx"
Task: "Component test for AuthenticatedLayout in src/frontend/tests/components/AuthenticatedLayout.test.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 0 (sign-off gate) and Phase 1 (baseline).
2. Complete Phase 2 (Foundational — CRITICAL, blocks all stories).
3. Complete Phase 3 (User Story 1 — wizard nav persistence).
4. **STOP and VALIDATE**: run T011/T012's tests and quickstart scenario 1 independently.
5. Demo if ready — this alone delivers the core "no more dead-end wizard" value.

### Incremental Delivery

1. Phase 0 + Phase 1 + Phase 2 → foundation ready.
2. Phase 3 (US1) → test independently → MVP demo.
3. Phase 4 (US2) → test independently → full visual consistency demo.
4. Phase 5 (US3) → test independently → capability-correctness demo.
5. Phase 6 (US4) → test independently → wayfinding polish demo.
6. Phase 7 → full regression + Principle IX final acceptance → feature complete.

## Notes

- [P] tasks touch different files with no dependency on an incomplete task.
- Phases 5 and 6 are largely verification of logic already built in Phase 2 (T004), per data-model.md and research.md §2/§4 — this reflects that `NavBar`'s capability and active-route derivation is a single implementation serving three user stories (US3, US4) plus part of US1's acceptance criteria, not three separate builds.
- Do not implement a Refresh button as part of this feature (contracts/nav-bar.md's Open Item) — that is `019-spa-refresh-button`'s scope, gated by T001's decision only insofar as it determines the trailing-cluster layout, not its behavior.
- Coordinate T010's edit to `ProtectedRoute.jsx` with `019-spa-refresh-button`'s separate MSAL-timing edit to the same file (plan.md's Cross-Feature Dependencies section) — additive, non-conflicting, but whichever PR merges second should rebase.
