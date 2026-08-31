---

description: "Task list for In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)"
---

# Tasks: In-App Screen Refresh & Reload Resilience

**Input**: Design documents from `/specs/019-spa-refresh-button/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/refresh-control.md, contracts/reload-resilience.md, quickstart.md

**Tests**: Explicitly required — the constitution's Principle I (Meaningful, Automated Testing, NON-NEGOTIABLE) mandates an automated test for every distinct outcome; FR-001 through FR-011 each map to one. Test tasks are included throughout.

**Organization**: Tasks are grouped by user story (spec.md: US1 = P1 in-app refresh control, US2 = P1 browser reload resilience, US3 = P3 unsaved-changes warning). **Updated 2026-08-31** (`/speckit-analyze` remediation): `022-persistent-nav-redesign` has since merged to `main` (`1b79aa8`, `5a4dce6`), so US1's mounting tasks are no longer externally blocked — `NavBar.jsx`/`TitleBar.jsx` exist with a reserved mount point. This surfaced a smaller wiring gap (a page can't hand props to the sibling-rendered nav bar), closed with a new `RefreshContext` (T008a). **Read "Dependencies & Execution Order" before starting** for the current build order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no same-phase dependency)
- **[Story]**: US1 / US2 / US3 — omitted for Setup, Foundational, and Polish tasks

## Path Conventions

Frontend-only feature within the existing web-application layout: `src/frontend/` (React/Vite), per plan.md's Project Structure. No `src/backend/` or `infrastructure/terraform/` changes.

---

## Phase 1: Setup

**Purpose**: Record the Constitution Principle XI design sign-off this feature's visible UI element requires, before any implementation begins.

- [x] T001 **UI design agreement/sign-off** (Constitution Principle XI, NON-NEGOTIABLE): the requesting user or product owner confirms the refresh control design already merged onto the `022-persistent-nav-redesign` branch (PR #79, commit `4a43123`) — a `.btn.btn-ghost` button with an inlined Lucide `refresh-cw` icon and "Refresh" label, shown in the persistent nav bar on `specs/designs/02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`, and in the title bar on `03-play.html`, documented in `specs/designs/README.md`'s "## Refresh" section — as the design to implement per `contracts/refresh-control.md`. This task is not complete until that confirmation is given; the merged mockup existing is not sufficient on its own. **Confirmed by the requesting user (Reza Mahmood) in-session on 2026-08-31.** **Gates T008 and every US1 mounting task below (T009–T011).** Does not gate US2/US3 (no novel visual element — T018's login copy is a one-line text addition to an existing screen, not a new UI element requiring separate mockup agreement).

**Checkpoint**: Design confirmed — UI-visible implementation work may begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**None required beyond T001.** Unlike a typical feature, US1/US2/US3 here share no common data model, service, or backend layer to stand up first — each story's hook/component/fix is self-contained (see plan.md's Technical Context: this is a frontend-only feature with no new backend, storage, or shared entity). Proceed directly to the user story phases.

---

## Phase 3: User Story 1 - Refresh a Screen Without Leaving It (Priority: P1)

**Goal**: Every current authenticated, data-showing screen (Main Menu, Admin Accounts, Admin Story Wizard) gets a visible refresh control that re-fetches that screen's data in place — never navigating away, signing the user out, or resetting the wizard's current step (FR-001–FR-005).

**Independent Test**: Open an authenticated screen, select its refresh control, and confirm the screen's data updates while the user remains on the same screen; select it twice in quick succession and confirm only one request fires; force a failure and confirm an inline, non-blocking error appears without the screen going blank.

### Tests for User Story 1

- [x] T002 [P] [US1] Add `src/frontend/tests/hooks/useRefreshable.test.jsx`: a second `refresh()` call while one is already pending is a no-op (FR-004); a rejected fetch sets `error` without throwing and leaves prior `data` unchanged (FR-005); a successful fetch replaces `data` and clears `error`; `refresh()` fires once automatically on mount
- [x] T002a [P] [US1] Add `src/frontend/tests/context/RefreshContext.test.jsx`: `usePublishRefresh` sets the context value while the publishing component is mounted and clears it on unmount; `useRefreshContext()` returns `null` when nothing has published
- [x] T003 [P] [US1] Add `src/frontend/tests/components/RefreshButton.test.jsx`: renders `.btn.btn-ghost` with the icon + "Refresh" label per `contracts/refresh-control.md`'s agreed markup; is `disabled` and shows "Refreshing…" while `loading`; calls `onClick` when activated
- [x] T003a [P] [US1] Add `src/frontend/tests/components/NavBar.test.jsx` (or extend, if one exists): renders `RefreshButton` inside `data-nav-slot="trailing-actions"` only when `RefreshContext` has a published value; renders nothing there otherwise (e.g. on `/login`)
- [x] T004 [P] [US1] Add `src/frontend/tests/integration/main_menu_refresh.test.jsx`: selecting the refresh control re-fetches capabilities and updates the visible menu items without navigating or signing out (extends the existing `useCapabilities`/`MainMenu` test patterns in `src/frontend/tests/components/MainMenu.test.jsx` / `src/frontend/tests/hooks/useCapabilities.test.jsx`)
- [x] T004a [US1] Add `src/frontend/tests/integration/main_menu_permissions_refresh.test.jsx` (added 2026-08-31, `/speckit-analyze` remediation — FR-011, spec.md Edge Cases: "user's permissions change on the server between when a screen was loaded and when it is refreshed"): mock `GET /api/auth/me` to return a reduced capability set on the refresh call versus the initial mount call; assert the refreshed `MainMenu` reflects the reduced capabilities (e.g. an admin-only item present after load disappears after refresh), distinct from the general re-fetch assertion in T004
- [x] T005 [P] [US1] Add `src/frontend/tests/integration/admin_accounts_refresh.test.jsx`: selecting the refresh control re-fetches the account list; simulating a rejected `listAccounts` call shows an inline error and leaves the previously-loaded list visible (closes the existing uncaught-exception gap in `AdminAccountsPage.jsx`)
- [x] T006 [US1] Extend `src/frontend/tests/integration/admin_story_creation_flow.test.jsx` (or add a sibling file): selecting the wizard's refresh control re-fetches the current draft and leaves `activeStep` unchanged (FR-003)

### Implementation for User Story 1

- [x] T007 [P] [US1] Create `src/frontend/src/hooks/useRefreshable.js` implementing the contract in `contracts/refresh-control.md` / data-model.md's Refreshable Data State: `{ data, loading, error, refresh }`, in-flight guard, no propagation of a rejected fetch to a caller `ErrorBoundary`
- [x] T007a [P] [US1] Create `src/frontend/src/context/RefreshContext.jsx` (added 2026-08-31, `/speckit-analyze` remediation) per `contracts/refresh-control.md`'s `RefreshContext` section: `RefreshProvider`, `usePublishRefresh({ refresh, loading })`, `useRefreshContext()`. Solves the wiring gap left by `022-persistent-nav-redesign` — `NavBar`/`TitleBar` render as siblings of page content under `AuthenticatedLayout.jsx`, not parents, so a page needs this to hand its refresh state up to them
- [x] T007b [US1] Wrap `AuthenticatedLayout.jsx`'s children in `<RefreshProvider>` (single mount point near the app root, above where `NavBar`/`TitleBar` and page content both render) — depends on T007a
- [x] T008 [US1] Create `src/frontend/src/components/Common/RefreshButton.jsx` using the exact markup agreed in `contracts/refresh-control.md` (`.btn.btn-ghost`, inlined Lucide `refresh-cw` SVG copied from `specs/designs/02-story-select.html`, "Refresh"/"Refreshing…" label, `disabled` while loading) — **depends on T001**
- [x] T008b [US1] Modify `src/frontend/src/components/Layout/NavBar.jsx` (added 2026-08-31, post-022-merge): consume `useRefreshContext()`; when non-null, render `RefreshButton` (T008) inside the existing `data-nav-slot="trailing-actions"` span — depends on T007a, T007b, T008
- [x] T009 [US1] Mount `useRefreshable` (T007) on `src/frontend/src/components/Menu/MainMenu.jsx` and publish its `{ refresh, loading }` via `usePublishRefresh` (T007a), replacing its existing ad hoc `refetch`/"Refresh" button in the no-capabilities state and adding refresh to the has-capabilities state where none exists today — depends on T007, T007a, T008b
- [x] T010 [US1] Mount `useRefreshable` on `src/frontend/src/pages/AdminAccountsPage.jsx` and publish via `usePublishRefresh`; add a caught-error inline message (reusing `MainMenu`'s existing error-state pattern) so a failed refresh no longer risks the top-level `ErrorBoundary` (FR-005) — depends on T007, T007a, T008b
- [x] T011 [US1] Mount `useRefreshable` on `src/frontend/src/pages/AdminStoryWizardPage.jsx` for the draft re-fetch and publish via `usePublishRefresh`, confirming `activeStep` is untouched by a refresh (FR-003) — depends on T007, T007a, T008b

**Checkpoint**: `useRefreshable`/`RefreshButton`/`RefreshContext` exist and are fully tested in isolation, and are mounted end-to-end on all three real screens via `NavBar`'s `trailing-actions` slot.

---

## Phase 4: User Story 2 - Browser Reload No Longer Breaks the App (Priority: P1)

**Goal**: A browser reload (or direct URL open, or back/forward navigation) at any authenticated screen — including nested admin routes — never shows an error page, never forces re-authentication for a still-valid session, and gives a clear explanation when the session genuinely has expired (FR-006–FR-009).

**Independent Test**: Navigate to a nested route (e.g., `/admin/stories/new`), reload the browser natively, and confirm the same screen loads with no error and no re-authentication prompt; then invalidate the session and reload again, confirming a clear explanation appears on the sign-in screen instead of a generic error.

**No dependency on `022-persistent-nav-redesign`** — every file this story touches (`ProtectedRoute.jsx`, `staticwebapp.config.json`, `useCapabilities.js`, `LoginScreen.jsx`) is untouched by 022's scope. This story can be implemented immediately.

### Tests for User Story 2

- [x] T012 [P] [US2] Add `src/frontend/tests/components/ProtectedRoute.test.jsx` (or extend an existing one if present): covers all four combinations of MSAL `inProgress` (`InteractionStatus.Startup`/`None`) × `isAuthenticated` (`true`/`false`) per `contracts/reload-resilience.md` Guarantee 2 — asserts a loading state (not a redirect) while `inProgress !== InteractionStatus.None`, and correct redirect/render behavior once initialization completes
- [x] T013 [P] [US2] Add `src/frontend/tests/integration/reload_resilience.test.jsx`: remounts the app tree with a pre-populated MSAL mock (simulating a hard reload with a valid cached session) on a nested route and asserts no premature redirect to `/login` occurs before MSAL initialization completes
- [x] T014 [P] [US2] Extend `src/frontend/tests/components/LoginScreen.test.jsx` (or create it): asserts the `sessionExpired` message renders when `location.state?.reason === "session-expired"` and is absent otherwise

### Implementation for User Story 2

- [x] T015 [P] [US2] Create `src/frontend/staticwebapp.config.json` per `contracts/reload-resilience.md` Guarantee 1: `navigationFallback.rewrite` to `/index.html`, excluding `/api/*` (the linked Function App backend) and static asset extensions
- [x] T016 [US2] Modify `src/frontend/src/components/Auth/ProtectedRoute.jsx` per `contracts/reload-resilience.md` Guarantee 2: read `useMsal().inProgress`; render a loading state while `inProgress !== InteractionStatus.None`; only evaluate `isAuthenticated` (and the existing capability check) once initialization completes
- [x] T017 [P] [US2] Modify `src/frontend/src/hooks/useCapabilities.js`'s existing `REDIRECT_ATTEMPTED_KEY`-guarded 401 handler per `contracts/reload-resilience.md` Guarantee 3 / research.md §4: instead of calling `instance.loginRedirect(loginRequest)` immediately, navigate to `/login` with `state: { reason: "session-expired" }` so the user sees `LoginScreen`'s explanation before re-authenticating
- [x] T018 [US2] Modify `src/frontend/src/components/Login/LoginScreen.jsx`: add a `sessionExpired: "Your session ended — please sign in again."` entry to the existing `MESSAGES` map; on mount, read `useLocation().state?.reason` and seed `status`/`message` from it when equal to `"session-expired"` — depends on T017

**Checkpoint**: User Story 2 is independently functional and fully deployable on its own, regardless of US1/US3 or 022's status.

---

## Phase 5: User Story 3 - Warning Before Losing Unsaved Input (Priority: P3)

**Goal**: A user filling in the story-creation wizard is warned by the browser's native mechanism before a reload or close would discard unsaved input (FR-010).

**Independent Test**: Start typing in a wizard step without saving, attempt to reload or close the tab, and confirm the browser's native confirmation prompt appears; confirm no prompt appears when there is no unsaved input.

**No dependency on `022-persistent-nav-redesign`** — this story changes `AdminStoryWizardPage.jsx`'s internal dirty-tracking, not its header/layout, and 022's own Assumptions state wizard save behavior is unchanged by that feature.

### Tests for User Story 3

- [x] T019 [P] [US3] Add `src/frontend/tests/hooks/useUnsavedChangesWarning.test.jsx`: the `beforeunload` listener is attached only while `isDirty` is `true` and removed once it flips back to `false`
- [x] T020 [US3] Extend `src/frontend/tests/integration/admin_story_creation_flow.test.jsx` (or the file from T006): dirtying a step's field arms the warning; a successful save (`patchDraft`/`postMessage`) clears it

### Implementation for User Story 3

- [x] T021 [P] [US3] Create `src/frontend/src/hooks/useUnsavedChangesWarning.js` per data-model.md's Unsaved-Changes Flag: attaches/detaches a standard `beforeunload` handler based on an `isDirty` boolean input
- [x] T022 [US3] Wire `isDirty` tracking into `src/frontend/src/pages/AdminStoryWizardPage.jsx` (true from the moment a tracked step field changes until the next successful `patchDraft`/`postMessage` completes) and pass it to `useUnsavedChangesWarning` (T021) — depends on T021

**Checkpoint**: All three user stories are independently functional (US1 partially, pending 022 — see below).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against the real deployed environment, per Constitution Principle IX.

- [ ] T023 Run all 8 scenarios in `quickstart.md` against a local/staging build as an implementation self-check (agent-run; does not satisfy T024). **Blocked 2026-08-31**: the implementing agent's environment has no Node.js/npm installed (`src/frontend`'s toolchain — CI uses Node 24 per `.github/workflows/test.yml`), so neither `npm test` (Vitest suite for T002–T022's new/extended tests) nor a served build for the manual quickstart walkthrough could be run here. All T002–T022 code and tests were written and self-reviewed for consistency with their contracts, but are unverified by an actual test run. Whoever picks this up next with a working Node environment should run `npm test` in `src/frontend` first before attempting T023's manual scenarios.
- [ ] T024 **User-verified acceptance** (Constitution Principle IX, NON-NEGOTIABLE): the requesting user or product owner — not the implementing agent — runs `quickstart.md`'s full scenario set end-to-end against the real deployed environment (or the most representative environment available), including the reload-on-nested-route scenario (Scenario 4) which automated tests cannot fully validate against real Azure Static Web Apps routing (per Principle IX's own rationale). This task is not complete until that confirmation is given — depends on T023 and on all of US1/US2/US3 being implemented (no story is externally blocked as of 2026-08-31; see Dependencies & Execution Order).

---

## Dependencies & Execution Order

### Cross-feature sequencing: 022-persistent-nav-redesign (resolved 2026-08-31)

`022-persistent-nav-redesign` has merged to `main` (`1b79aa8`, `5a4dce6`; PRs #103/#104). `src/frontend/src/components/Layout/NavBar.jsx` and `TitleBar.jsx` exist, restyling of `MainMenu.jsx`/`AdminAccountsPage.jsx`/`AdminStoryWizardPage.jsx` from 022's own scope is already done, and `NavBar.jsx` reserves a `data-nav-slot="trailing-actions"` mount point specifically for this feature's `RefreshButton`. **US1's mounting tasks (T009–T011) are no longer blocked.**

Reviewing the merged code surfaced one remaining gap, not related to 022: `AuthenticatedLayout.jsx` renders `NavBar`/`TitleBar` as a **sibling** of the active page's content, not a parent, so a page has no prop-based way to reach the nav bar's `trailing-actions` slot. T007a/T007b/T008b (`RefreshContext`) close this gap — see `contracts/refresh-control.md`'s `RefreshContext` section for why a context was chosen over lifting `NavBar` into each page (it would undo 022's centralization).

- **T007/T008/T007a/T007b/T008b** (hook, button, context, provider mount, `NavBar` consumption) have no dependency on 022 beyond the merged `NavBar.jsx` file itself existing, which it now does.
- **US1's per-page mounting (T009–T011)** now only depends on T007, T007a, T008b — all in-repo, no external feature dependency remains.
- **US2 and US3** were never dependent on 022 and remain unblocked.

**Recommended build order**: **T001 → T007/T007a/T003/T003a (parallelizable) → T007b → T008/T008b → T009–T011 (US1 mounting) → US2 (T012–T018) → US3 (T019–T022) → T023/T024.** US1 can now go end-to-end first since nothing external blocks it; US2 remains equally safe to build in parallel or first if preferred (both are P1 with no shared files).

### Phase Dependencies

- **Setup (Phase 1)**: T001 only — no dependencies, start immediately. Gates T008 and T009–T011.
- **Foundational (Phase 2)**: None — proceed directly to user stories.
- **User Stories (Phase 3+)**: US1, US2, and US3 can all start immediately and in parallel — no external blockers remain. Within US1, T009–T011 depend on T007, T007a, and T008b completing first (see task list).
- **Polish (Phase 6)**: T023/T024 depend on all three user stories being implemented.

### Within Each User Story

- Tests are written before implementation and should fail first.
- Hooks before components; components before mounting into a page.
- Each story's checkpoint is independently testable before moving to the next.

### Parallel Opportunities

- T002, T002a, T003, T003a, T004, T004a, T005 (all US1 tests) can run in parallel — different files.
- T012, T013, T014 (all US2 tests) can run in parallel — different files.
- T015 (staticwebapp.config.json) can run in parallel with T012–T014 — no shared files.
- T019 (US3 test) can run in parallel with any US2 task.
- Once T001 clears, T007/T007a (hook, context) and T003's underlying component work can proceed in parallel with all of US2/US3; T008b/T009–T011 depend on T007a/T007b/T008 landing first.

---

## Parallel Example: User Story 2 (unblocked, highest-priority next step)

```bash
# Launch all three US2 test files together:
Task: "ProtectedRoute.test.jsx — inProgress x isAuthenticated matrix"
Task: "reload_resilience.test.jsx — hard reload on a nested route"
Task: "LoginScreen.test.jsx — sessionExpired message present/absent"

# Then implement:
Task: "Create src/frontend/staticwebapp.config.json"
Task: "Modify ProtectedRoute.jsx to gate on inProgress"
Task: "Modify useCapabilities.js's 401 handler to navigate with a reason"
Task: "Modify LoginScreen.jsx to render the sessionExpired message"
```

---

## Implementation Strategy

### Recommended First Increment

With `022-persistent-nav-redesign` merged, no story is externally blocked, so the build order can follow spec.md's own priority listing:

1. Complete Phase 1: T001 (sign-off)
2. Complete Phase 3: User Story 1 (T002–T011, including the new T007a/T007b/T008b `RefreshContext` wiring)
3. **STOP and VALIDATE**: run quickstart.md's US1 scenarios against a real/staging deployment
4. Complete Phase 4: User Story 2 (T012–T018) — addresses the spec's headline complaint ("the browser's refresh button will kill the app") and remains safe to build in parallel with US1 if preferred, since the two share no files
5. **STOP and VALIDATE**: run quickstart.md Scenarios 4–6 against a real deployment
6. Deploy/demo

### Incremental Delivery From There

1. Add User Story 3 (T019–T022) → test independently → deploy/demo
2. Run T023 (self-check) then T024 (final user-verified acceptance) covering all three stories

### Parallel Team Strategy

With multiple developers: one takes US1 (T002–T011), a second takes US2 (T012–T018), a third takes US3 (T019–T022) — the only cross-story dependency is that US1's T009–T011 need T007/T007a/T008b done first within that same track.
