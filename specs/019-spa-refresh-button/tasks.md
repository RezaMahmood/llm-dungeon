---

description: "Task list for In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)"
---

# Tasks: In-App Screen Refresh & Reload Resilience

**Input**: Design documents from `/specs/019-spa-refresh-button/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/refresh-control.md, contracts/reload-resilience.md, quickstart.md

**Tests**: Explicitly required — the constitution's Principle I (Meaningful, Automated Testing, NON-NEGOTIABLE) mandates an automated test for every distinct outcome; FR-001 through FR-011 each map to one. Test tasks are included throughout.

**Organization**: Tasks are grouped by user story (spec.md: US1 = P1 in-app refresh control, US2 = P1 browser reload resilience, US3 = P3 unsaved-changes warning). **Read "Dependencies & Execution Order" before starting** — US1's visible mounting tasks are blocked on an external feature (`022-persistent-nav-redesign`) and the recommended build order does not match spec.md's story listing order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no same-phase dependency)
- **[Story]**: US1 / US2 / US3 — omitted for Setup, Foundational, and Polish tasks

## Path Conventions

Frontend-only feature within the existing web-application layout: `src/frontend/` (React/Vite), per plan.md's Project Structure. No `src/backend/` or `infrastructure/terraform/` changes.

---

## Phase 1: Setup

**Purpose**: Record the Constitution Principle XI design sign-off this feature's visible UI element requires, before any implementation begins.

- [ ] T001 **UI design agreement/sign-off** (Constitution Principle XI, NON-NEGOTIABLE): the requesting user or product owner confirms the refresh control design already merged onto the `022-persistent-nav-redesign` branch (PR #79, commit `4a43123`) — a `.btn.btn-ghost` button with an inlined Lucide `refresh-cw` icon and "Refresh" label, shown in the persistent nav bar on `specs/designs/02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`, and in the title bar on `03-play.html`, documented in `specs/designs/README.md`'s "## Refresh" section — as the design to implement per `contracts/refresh-control.md`. This task is not complete until that confirmation is given; the merged mockup existing is not sufficient on its own. **Gates T008 and every US1 mounting task below (T009–T011).** Does not gate US2/US3 (no novel visual element — T018's login copy is a one-line text addition to an existing screen, not a new UI element requiring separate mockup agreement).

**Checkpoint**: Design confirmed — UI-visible implementation work may begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**None required beyond T001.** Unlike a typical feature, US1/US2/US3 here share no common data model, service, or backend layer to stand up first — each story's hook/component/fix is self-contained (see plan.md's Technical Context: this is a frontend-only feature with no new backend, storage, or shared entity). Proceed directly to the user story phases.

---

## Phase 3: User Story 1 - Refresh a Screen Without Leaving It (Priority: P1)

**Goal**: Every current authenticated, data-showing screen (Main Menu, Admin Accounts, Admin Story Wizard) gets a visible refresh control that re-fetches that screen's data in place — never navigating away, signing the user out, or resetting the wizard's current step (FR-001–FR-005).

**Independent Test**: Open an authenticated screen, select its refresh control, and confirm the screen's data updates while the user remains on the same screen; select it twice in quick succession and confirm only one request fires; force a failure and confirm an inline, non-blocking error appears without the screen going blank. **Note**: T009–T011 (actually mounting the control on a real screen) are blocked pending `022-persistent-nav-redesign` — see Dependencies & Execution Order. Until then, this story's independent test is exercised at the hook/component level (T002–T003), not end-to-end on a live screen.

### Tests for User Story 1

- [ ] T002 [P] [US1] Add `src/frontend/tests/hooks/useRefreshable.test.jsx`: a second `refresh()` call while one is already pending is a no-op (FR-004); a rejected fetch sets `error` without throwing and leaves prior `data` unchanged (FR-005); a successful fetch replaces `data` and clears `error`; `refresh()` fires once automatically on mount
- [ ] T003 [P] [US1] Add `src/frontend/tests/components/RefreshButton.test.jsx`: renders `.btn.btn-ghost` with the icon + "Refresh" label per `contracts/refresh-control.md`'s agreed markup; is `disabled` and shows "Refreshing…" while `loading`; calls `onClick` when activated
- [ ] T004 [P] [US1] Add `src/frontend/tests/integration/main_menu_refresh.test.jsx`: selecting the refresh control re-fetches capabilities and updates the visible menu items without navigating or signing out (extends the existing `useCapabilities`/`MainMenu` test patterns in `src/frontend/tests/components/MainMenu.test.jsx` / `src/frontend/tests/hooks/useCapabilities.test.jsx`)
- [ ] T005 [P] [US1] Add `src/frontend/tests/integration/admin_accounts_refresh.test.jsx`: selecting the refresh control re-fetches the account list; simulating a rejected `listAccounts` call shows an inline error and leaves the previously-loaded list visible (closes the existing uncaught-exception gap in `AdminAccountsPage.jsx`)
- [ ] T006 [US1] Extend `src/frontend/tests/integration/admin_story_creation_flow.test.jsx` (or add a sibling file): selecting the wizard's refresh control re-fetches the current draft and leaves `activeStep` unchanged (FR-003)

### Implementation for User Story 1

- [ ] T007 [P] [US1] Create `src/frontend/src/hooks/useRefreshable.js` implementing the contract in `contracts/refresh-control.md` / data-model.md's Refreshable Data State: `{ data, loading, error, refresh }`, in-flight guard, no propagation of a rejected fetch to a caller `ErrorBoundary`
- [ ] T008 [US1] Create `src/frontend/src/components/Common/RefreshButton.jsx` using the exact markup agreed in `contracts/refresh-control.md` (`.btn.btn-ghost`, inlined Lucide `refresh-cw` SVG copied from `specs/designs/02-story-select.html`, "Refresh"/"Refreshing…" label, `disabled` while loading) — **depends on T001**
- [ ] T009 [US1] ⚠ **BLOCKED — depends on `022-persistent-nav-redesign` landing** (see Dependencies & Execution Order): mount `RefreshButton` (T008) + `useRefreshable` (T007) inside the persistent nav bar on `src/frontend/src/components/Menu/MainMenu.jsx`, replacing its existing ad hoc `refetch`/"Refresh" button in the no-capabilities state with the shared component, and adding it to the has-capabilities state where none exists today
- [ ] T010 [US1] ⚠ **BLOCKED — depends on `022-persistent-nav-redesign` landing**: mount `RefreshButton` + `useRefreshable` inside the persistent nav bar on `src/frontend/src/pages/AdminAccountsPage.jsx`, and add a caught-error inline message (reusing `MainMenu`'s existing error-state pattern) so a failed refresh no longer risks the top-level `ErrorBoundary` (FR-005) — depends on T007, T008
- [ ] T011 [US1] ⚠ **BLOCKED — depends on `022-persistent-nav-redesign` landing**: mount `RefreshButton` + `useRefreshable` inside the persistent nav bar on `src/frontend/src/pages/AdminStoryWizardPage.jsx` for the draft re-fetch, confirming `activeStep` is untouched by a refresh (FR-003) — depends on T007, T008

**Checkpoint**: `useRefreshable`/`RefreshButton` exist and are fully tested in isolation; they are not yet visible on any real screen until 022 unblocks T009–T011.

---

## Phase 4: User Story 2 - Browser Reload No Longer Breaks the App (Priority: P1)

**Goal**: A browser reload (or direct URL open, or back/forward navigation) at any authenticated screen — including nested admin routes — never shows an error page, never forces re-authentication for a still-valid session, and gives a clear explanation when the session genuinely has expired (FR-006–FR-009).

**Independent Test**: Navigate to a nested route (e.g., `/admin/stories/new`), reload the browser natively, and confirm the same screen loads with no error and no re-authentication prompt; then invalidate the session and reload again, confirming a clear explanation appears on the sign-in screen instead of a generic error.

**No dependency on `022-persistent-nav-redesign`** — every file this story touches (`ProtectedRoute.jsx`, `staticwebapp.config.json`, `useCapabilities.js`, `LoginScreen.jsx`) is untouched by 022's scope. This story can be implemented immediately.

### Tests for User Story 2

- [ ] T012 [P] [US2] Add `src/frontend/tests/components/ProtectedRoute.test.jsx` (or extend an existing one if present): covers all four combinations of MSAL `inProgress` (`InteractionStatus.Startup`/`None`) × `isAuthenticated` (`true`/`false`) per `contracts/reload-resilience.md` Guarantee 2 — asserts a loading state (not a redirect) while `inProgress !== InteractionStatus.None`, and correct redirect/render behavior once initialization completes
- [ ] T013 [P] [US2] Add `src/frontend/tests/integration/reload_resilience.test.jsx`: remounts the app tree with a pre-populated MSAL mock (simulating a hard reload with a valid cached session) on a nested route and asserts no premature redirect to `/login` occurs before MSAL initialization completes
- [ ] T014 [P] [US2] Extend `src/frontend/tests/components/LoginScreen.test.jsx` (or create it): asserts the `sessionExpired` message renders when `location.state?.reason === "session-expired"` and is absent otherwise

### Implementation for User Story 2

- [ ] T015 [P] [US2] Create `src/frontend/staticwebapp.config.json` per `contracts/reload-resilience.md` Guarantee 1: `navigationFallback.rewrite` to `/index.html`, excluding `/api/*` (the linked Function App backend) and static asset extensions
- [ ] T016 [US2] Modify `src/frontend/src/components/Auth/ProtectedRoute.jsx` per `contracts/reload-resilience.md` Guarantee 2: read `useMsal().inProgress`; render a loading state while `inProgress !== InteractionStatus.None`; only evaluate `isAuthenticated` (and the existing capability check) once initialization completes
- [ ] T017 [P] [US2] Modify `src/frontend/src/hooks/useCapabilities.js`'s existing `REDIRECT_ATTEMPTED_KEY`-guarded 401 handler per `contracts/reload-resilience.md` Guarantee 3 / research.md §4: instead of calling `instance.loginRedirect(loginRequest)` immediately, navigate to `/login` with `state: { reason: "session-expired" }` so the user sees `LoginScreen`'s explanation before re-authenticating
- [ ] T018 [US2] Modify `src/frontend/src/components/Login/LoginScreen.jsx`: add a `sessionExpired: "Your session ended — please sign in again."` entry to the existing `MESSAGES` map; on mount, read `useLocation().state?.reason` and seed `status`/`message` from it when equal to `"session-expired"` — depends on T017

**Checkpoint**: User Story 2 is independently functional and fully deployable on its own, regardless of US1/US3 or 022's status.

---

## Phase 5: User Story 3 - Warning Before Losing Unsaved Input (Priority: P3)

**Goal**: A user filling in the story-creation wizard is warned by the browser's native mechanism before a reload or close would discard unsaved input (FR-010).

**Independent Test**: Start typing in a wizard step without saving, attempt to reload or close the tab, and confirm the browser's native confirmation prompt appears; confirm no prompt appears when there is no unsaved input.

**No dependency on `022-persistent-nav-redesign`** — this story changes `AdminStoryWizardPage.jsx`'s internal dirty-tracking, not its header/layout, and 022's own Assumptions state wizard save behavior is unchanged by that feature.

### Tests for User Story 3

- [ ] T019 [P] [US3] Add `src/frontend/tests/hooks/useUnsavedChangesWarning.test.jsx`: the `beforeunload` listener is attached only while `isDirty` is `true` and removed once it flips back to `false`
- [ ] T020 [US3] Extend `src/frontend/tests/integration/admin_story_creation_flow.test.jsx` (or the file from T006): dirtying a step's field arms the warning; a successful save (`patchDraft`/`postMessage`) clears it

### Implementation for User Story 3

- [ ] T021 [P] [US3] Create `src/frontend/src/hooks/useUnsavedChangesWarning.js` per data-model.md's Unsaved-Changes Flag: attaches/detaches a standard `beforeunload` handler based on an `isDirty` boolean input
- [ ] T022 [US3] Wire `isDirty` tracking into `src/frontend/src/pages/AdminStoryWizardPage.jsx` (true from the moment a tracked step field changes until the next successful `patchDraft`/`postMessage` completes) and pass it to `useUnsavedChangesWarning` (T021) — depends on T021

**Checkpoint**: All three user stories are independently functional (US1 partially, pending 022 — see below).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against the real deployed environment, per Constitution Principle IX.

- [ ] T023 Run all 8 scenarios in `quickstart.md` against a local/staging build as an implementation self-check (agent-run; does not satisfy T024)
- [ ] T024 **User-verified acceptance** (Constitution Principle IX, NON-NEGOTIABLE): the requesting user or product owner — not the implementing agent — runs `quickstart.md`'s full scenario set end-to-end against the real deployed environment (or the most representative environment available), including the reload-on-nested-route scenario (Scenario 4) which automated tests cannot fully validate against real Azure Static Web Apps routing (per Principle IX's own rationale). This task is not complete until that confirmation is given — depends on T023 and on whichever of US1/US2/US3 have been unblocked and implemented at that point.

---

## Dependencies & Execution Order

### Cross-feature sequencing: should 019 wait for 022-persistent-nav-redesign?

**Partially.** As of this writing, `022-persistent-nav-redesign` has an open PR (#79) with the agreed mockups merged onto its branch, but has not itself been through `/speckit-plan`/`/speckit-tasks` — its persistent nav bar does not exist as a React component yet, and its own scope (FR-010) requires restyling the exact same screens (`MainMenu.jsx`, `AdminAccountsPage.jsx`, `AdminStoryWizardPage.jsx`) that this feature's US1 needs to touch to mount the refresh control.

- **US1's mounting tasks (T009–T011) are blocked on 022**, not merely "sequenced after it" as a preference. Building an interim, pre-022 placement now would mean throwaway layout work (022 will restructure these same headers into its new nav shell shortly), real merge-conflict risk between the two branches editing the same lines, and a visually inconsistent intermediate state — a refresh button with no nav bar around it, contradicting the design that was just signed off in T001. **Recommendation: do not implement T009–T011 until `022-persistent-nav-redesign` has a merged nav bar component to mount into.**
- **US2 has zero dependency on 022** and addresses the spec's most urgent complaint (P1 — "the browser's refresh button will kill the app"). Its files (`ProtectedRoute.jsx`, `staticwebapp.config.json`, `useCapabilities.js`, `LoginScreen.jsx`) don't overlap with 022's scope at all. **There is no reason to delay it.**
- **US3 has zero dependency on 022** either — it changes wizard state logic, not layout, and 022's own spec explicitly states wizard save behavior is unchanged by that feature. Some file-level overlap with 022's eventual `AdminStoryWizardPage.jsx` restyle is possible but low-risk (different concerns within the same file).
- **T007/T008 (the `useRefreshable` hook and `RefreshButton` component themselves) have no dependency on 022** — they're self-contained and fully testable in isolation now; only their *mounting* is blocked.

**Recommended build order** (deliberately reordering spec.md's US1-then-US2 listing, which reflects priority, not delivery sequencing): **T001 → US2 (T012–T018) → US3 (T019–T022) → T002/T003/T007/T008 (US1's non-blocked pieces) → [wait for 022] → T004–T006, T009–T011 → T023/T024.** This ships the two highest-value, unblocked fixes first, keeps the hook/component ready to go the moment 022 lands, and avoids any throwaway UI work.

### Phase Dependencies

- **Setup (Phase 1)**: T001 only — no dependencies, start immediately. Gates T008 and T009–T011 only (see above).
- **Foundational (Phase 2)**: None — proceed directly to user stories.
- **User Stories (Phase 3+)**: US2 and US3 have no external blockers and can start immediately in parallel. US1's tests/hook/component (T002, T003, T007, T008) can start immediately; its mounting tasks (T009–T011) are blocked on `022-persistent-nav-redesign` (see above).
- **Polish (Phase 6)**: T023/T024 depend on whichever stories are implemented at that point; T024 in particular should be re-run (or extended) once US1's mounting tasks eventually unblock and ship.

### Within Each User Story

- Tests are written before implementation and should fail first.
- Hooks before components; components before mounting into a page.
- Each story's checkpoint is independently testable before moving to the next.

### Parallel Opportunities

- T002, T003, T004, T005 (all US1 tests) can run in parallel — different files.
- T012, T013, T014 (all US2 tests) can run in parallel — different files.
- T015 (staticwebapp.config.json) can run in parallel with T012–T014 — no shared files.
- T019 (US3 test) can run in parallel with any US2 task.
- Once T001 clears, T007 and T003's underlying component work can proceed in parallel with all of US2/US3.

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

### Recommended First Increment (not spec.md's listed MVP — see sequencing note above)

Because US1's visible control is externally blocked, the practical first shippable increment is **User Story 2** (browser reload resilience), not User Story 1, even though spec.md lists US1 first:

1. Complete Phase 1: T001 (sign-off — gates only US1's visual pieces, so this can happen in parallel with starting US2)
2. Complete Phase 4: User Story 2 (T012–T018)
3. **STOP and VALIDATE**: run quickstart.md Scenarios 4–6 against a real deployment
4. Deploy/demo — this alone fixes the spec's headline complaint

### Incremental Delivery From There

1. Add User Story 3 (T019–T022) → test independently → deploy/demo
2. Build User Story 1's non-blocked pieces (T002, T003, T007, T008) → these sit ready but unmounted
3. Once `022-persistent-nav-redesign` merges its nav bar component → complete T004–T006, T009–T011 → deploy/demo
4. Run T023 (self-check) then T024 (final user-verified acceptance) covering whichever stories have shipped by that point — re-run once US1 completes if it ships in a later increment

### Parallel Team Strategy

With multiple developers: one takes US2 (T012–T018, no blockers), a second takes US3 (T019–T022, no blockers) and/or US1's non-blocked pieces (T002, T003, T007, T008) in parallel — none of these three tracks share a file. Nobody should start T009–T011 until 022 is confirmed merged.
