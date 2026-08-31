# Implementation Plan: In-App Screen Refresh & Reload Resilience

**Branch**: `019-spa-refresh-button` | **Date**: 2026-08-30 | **Spec**: `specs/019-spa-refresh-button/spec.md`

**Input**: Feature specification from `/specs/019-spa-refresh-button/spec.md`

## Summary

Give every authenticated, data-showing screen a visible in-app refresh control that re-fetches that screen's data in place (never navigating away, signing the user out, or resetting a wizard's current step), and stop the browser's own native reload from breaking the app on any screen — including nested admin routes. Investigation of the current frontend found two distinct root causes behind the "reload breaks the app" complaint: (1) `ProtectedRoute` reads MSAL's `isAuthenticated` before `MsalProvider` finishes reading the cached session from `localStorage`, so a hard reload can momentarily report a valid session as unauthenticated and redirect to `/login`; (2) there is no `staticwebapp.config.json` pinning Azure Static Web Apps' SPA fallback, so a direct reload/open of a nested route (e.g. `/admin/stories/new`) has no explicit, reviewable guarantee it resolves to the app shell rather than a platform 404. Both are fixed alongside a small shared `useRefreshable` hook + `RefreshButton` component that upgrades the ad hoc `refresh()` pattern already duplicated in `MainMenu`, `AdminAccountsPage`, and `AdminStoryWizardPage` into one reusable, in-flight-guarded, error-surfacing implementation.

This is a frontend-only feature. No backend endpoint, data model, or Azure resource changes are required: `/api/auth/me` already recomputes capabilities fresh on every call (satisfying FR-011 by construction), and every other screen's data comes from endpoints that are already safe to re-call.

## Technical Context

**Language/Version**: JavaScript (ES2022) + React 18 via Vite (frontend, existing) — no backend changes

**Primary Dependencies** (all existing, no additions):
- `react-router-dom` v6 (`BrowserRouter`, route matching) — `App.jsx`
- `@azure/msal-browser` / `@azure/msal-react` v3/v2 (`MsalProvider`, `useMsal`, `useIsAuthenticated`, `InteractionStatus`) — `AuthProvider.jsx`, `ProtectedRoute.jsx`
- `axios` — existing service layer (`accountService.js`, `authService.js`, `storyDraftService.js`)

**Storage**: N/A — no persistent entities introduced; MSAL's existing `localStorage`-backed token cache (`msalConfig.js`, `cacheLocation: "localStorage"`) is relied upon, not changed

**Testing**: Vitest + React Testing Library (`src/frontend/tests/{components,hooks,integration}`, existing convention) — new tests for `useRefreshable`, `RefreshButton`, `ProtectedRoute`'s initialization gating, and an integration test simulating a hard reload on a nested route

**Target Platform**: Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning` — this feature adds `src/frontend/public/staticwebapp.config.json` to pin navigation-fallback routing behavior

**Project Type**: Web application — frontend-only change to the existing `src/frontend/` structure; no `src/backend/` or `infrastructure/terraform/` changes

**Performance Goals**: N/A — no throughput/latency target specified (Principle IV); a refresh is a single existing re-fetch, no new round trips added

**Constraints**: **Updated 2026-08-30, post-design-sign-off** — the requesting product owner has since updated `specs/designs/02-story-select.html`, `03-play.html`, `04-admin-wizard.html`, `05-admin-users.html`, and `specs/designs/README.md` directly with the agreed control: a `.btn.btn-ghost` button, Lucide `refresh-cw` icon (inlined as a hand-copied SVG — no `lucide-react` package needed for one icon, per YAGNI) + a "Refresh" text label, mounted in the persistent top nav bar (title bar on the Play screen). This supersedes this plan's original "no icon" placement proposal. See research.md §7 and `contracts/refresh-control.md` for the confirmed markup.

**Updated 2026-08-31, post-022-merge** — `022-persistent-nav-redesign-done` has since landed on `main` (`1b79aa8`, `5a4dce6`; PRs #103/#104): `src/frontend/src/components/Layout/NavBar.jsx` and `TitleBar.jsx` now exist and each reserve an explicit `data-nav-slot="trailing-actions"` mount point for this feature's `RefreshButton`. The external blocker is gone. This surfaced a wiring gap 022 left unsolved (and shares with its own `onSaveCheckpoint`/`onPauseExit` props): `AuthenticatedLayout.jsx` renders `NavBar`/`TitleBar` as **siblings** of the page (`{isStoryPlay ? <TitleBar/> : <NavBar/>}` next to `{children}`), not as parents — so a page has no prop-based way to hand its `useRefreshable` state up to the nav bar beside it. This plan adds one new piece to close that gap: a small `RefreshContext` (provider + hook) that a page's `useRefreshable` publishes `{ refresh, loading }` into, which `NavBar` (and, later, `TitleBar` once the Play screen has real data) reads to render `RefreshButton` in its `trailing-actions` slot. Decision recorded 2026-08-31 (product owner + `/speckit-analyze` remediation): a context, not lifting `NavBar` rendering into each page, since the latter would undo 022's centralization of the nav bar and reintroduce the exact per-page header duplication 022 removed.

**Scale/Scope**: Applies to every current authenticated, data-showing screen: Main Menu (`/menu`), Admin Accounts (`/admin/accounts`), Admin Story Wizard (`/admin/stories/new`). `GamePage` (`/game`) and `AdminPage` (`/admin`) are still placeholders with no fetched data (008-core-gameplay / 005-story-publishing build their real content later) — the shared `useRefreshable`/`RefreshButton` pair is built once so those screens pick it up when they gain real data, but no placeholder screen gets a non-functional refresh control added just to satisfy FR-001's letter ahead of having data to refresh.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-002 through FR-011 each map to a distinct, testable behavior (successful refresh, overlapping-refresh guard, failed refresh, reload on a valid session, reload with an expired session, reload on a nested route, no forced re-auth on a valid reload, unsaved-input warning present/absent, permission re-evaluation on refresh). Phase 1's contracts define the `useRefreshable`/`RefreshButton` and routing-fallback behavior these tests assert against.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — `ProtectedRoute`'s fix only changes *when* it decides (waiting for MSAL initialization instead of judging early); it does not weaken the authenticated/capability check itself, and adds no new unauthenticated code path. The `staticwebapp.config.json` fallback rewrites to the app shell only — it does not expose any route or asset that bypasses `ProtectedRoute`'s or the backend's server-side authorization.

### Principle III – Defined Technology Stack
**Status**: ✓ MET — No new language, framework, or hosting model; no new dependency is added.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — One shared hook + one shared button component, reusing existing design-system classes and existing endpoints; the one new icon is inlined SVG copied from the agreed prototype rather than a new icon-library dependency; no client-side caching layer, no offline/service-worker machinery (none of which the spec asks for).

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing Vitest suite already wired into CI (`test.yml`); no new CI configuration needed.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: N/A — This feature makes no LLM calls and adds no LLM-adjacent surface.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: N/A — No new Azure resource dependency or inter-resource communication is introduced.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET — The refresh control is `.btn.btn-ghost` (updated 2026-08-30 to match the agreed prototypes — see Principle XI below), the same design-system class `MainMenu` already uses for its "Sign out" action; no ad hoc color, spacing, or font is introduced, and its Lucide `refresh-cw` icon is inlined SVG rather than a new icon-font/library dependency. It ships all four required interaction states because those states already live in the shared `.btn` styling, not per-instance. The routing fallback is invisible infrastructure with no visual surface.

### Principle IX – User-Verified Acceptance Before Completion (NON-NEGOTIABLE)
**Status**: Deferred to tasks.md — per constitution, `tasks.md` must end with an explicit final acceptance task verified by the requesting user against the real deployed environment, particularly for the reload-resilience behavior (FR-006/FR-007), which — per Principle IX's own rationale — automated tests cannot fully validate against real Azure Static Web Apps routing.

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: N/A — No new data is stored, logged, or displayed; refresh re-fetches data through existing, already-compliant endpoints.

### Principle XI – UI Design Pre-Agreement Before Implementation (NON-NEGOTIABLE)
**Status**: ✓ MET (updated 2026-08-30) — The requesting product owner has directly updated the hi-fi prototypes to show the agreed control: a ghost-styled, icon+label "Refresh" button (Lucide `refresh-cw`), mounted in the persistent nav bar on `02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`, and in the title bar on `03-play.html`, with `specs/designs/README.md` documenting it under a new "## Refresh" section ("Same treatment everywhere; it re-fetches the current view and never navigates."). This supersedes this plan's original per-screen-heading/no-icon proposal (which is retained in research.md §3 only as the reasoning trail). **`tasks.md` MUST still include an explicit UI design agreement/sign-off task, sequenced before all implementation tasks**, but it now records confirmation of *this* concrete, already-updated design rather than proposing a new one.
  - **Resolved 2026-08-31**: `022-persistent-nav-redesign-done` (the feature that owned building the persistent nav bar / title bar shown in the updated mockups) has merged to `main`. `NavBar.jsx`/`TitleBar.jsx` exist and reserve a `data-nav-slot="trailing-actions"` mount point for this feature's `RefreshButton`, so there is no remaining cross-feature sequencing question. The only remaining question was a wiring mechanism (how a page's refresh state reaches the sibling-rendered nav bar), resolved via a new `RefreshContext` — see Constraints above and Project Structure below.

No unjustified violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/019-spa-refresh-button/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── refresh-control.md
│   └── reload-resilience.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout, frontend-only (`src/frontend/`, established by `002-login-and-access-control`). No `src/backend/` or `infrastructure/terraform/` changes.

```text
src/frontend/
├── public/
│   └── staticwebapp.config.json      # NEW: pins SPA navigation-fallback rewrite (FR-006/SC-003) —
│                                     #   must live under public/ so Vite copies it into dist/,
│                                     #   which is what frontend-deploy.yml actually uploads
├── src/
│   ├── hooks/
│   │   ├── useRefreshable.js         # NEW: in-flight-guarded refresh state (loading/error/data), FR-002/FR-004/FR-005
│   │   └── useUnsavedChangesWarning.js  # NEW: wraps `beforeunload` behind an `isDirty` flag, FR-010/US3
│   ├── context/
│   │   └── RefreshContext.jsx        # NEW (added 2026-08-31): provider + `usePublishRefresh({ refresh, loading })`
│   │                                 #   + `useRefreshContext()` — lets a page (rendered as a sibling of
│   │                                 #   NavBar/TitleBar under AuthenticatedLayout) publish its
│   │                                 #   useRefreshable state for the nav bar to render; unset when the
│   │                                 #   active page hasn't published (e.g. Login) so NavBar renders
│   │                                 #   nothing in trailing-actions
│   ├── components/
│   │   └── Common/
│   │       ├── RefreshButton.jsx     # NEW: `.btn.btn-ghost` + inline Lucide `refresh-cw` SVG + "Refresh"
│   │                                 #   label, disabled+relabeled while refreshing — markup mirrors
│   │                                 #   specs/designs/{02,03,04,05}.html exactly (contracts/refresh-control.md)
│   │       └── ErrorBoundary.jsx     # unchanged
│   ├── components/Auth/
│   │   └── ProtectedRoute.jsx        # MODIFY: gate on MSAL `inProgress`/`InteractionStatus` before judging
│   │                                 #   `isAuthenticated`, so a hard reload doesn't redirect prematurely (FR-006/FR-007/FR-009)
│   ├── components/Layout/
│   │   └── NavBar.jsx                # MODIFY (added 2026-08-31, post-022-merge): consume RefreshContext via
│   │                                 #   useRefreshContext() and render RefreshButton in its existing
│   │                                 #   data-nav-slot="trailing-actions" span when a value is published
│   │                                 #   (FR-001/FR-002; TitleBar.jsx is left unchanged — the Play screen
│   │                                 #   it belongs to is still a placeholder per Scale/Scope below)
│   ├── components/Menu/
│   │   └── MainMenu.jsx              # MODIFY: adopt useRefreshable; publish { refresh, loading } via
│   │                                 #   usePublishRefresh into RefreshContext (no local button — NavBar
│   │                                 #   renders it); removes the existing ad hoc no-capabilities-only
│   │                                 #   refresh button, replaced by the shared control
│   ├── pages/
│   │   ├── AdminAccountsPage.jsx     # MODIFY: adopt useRefreshable; publish via usePublishRefresh; add
│   │                                 #   try/catch so a failed refresh shows an inline error instead of
│   │                                 #   hitting ErrorBoundary
│   │   └── AdminStoryWizardPage.jsx  # MODIFY: adopt useRefreshable for the draft re-fetch; publish via
│   │                                 #   usePublishRefresh; wire useUnsavedChangesWarning to in-progress
│   │                                 #   step edits (FR-010)
│   └── services/
│       └── authService.js            # MODIFY (small): expose a distinguishable "session expired" reason
│                                     #   so the login screen can show FR-008's "clear explanation"
└── tests/
    ├── hooks/
    │   ├── useRefreshable.test.jsx           # NEW
    │   └── useUnsavedChangesWarning.test.jsx # NEW
    ├── context/
    │   └── RefreshContext.test.jsx           # NEW: publish → NavBar-side consumption round-trip; unset
    │                                         #   when nothing has published
    ├── components/
    │   ├── RefreshButton.test.jsx            # NEW
    │   ├── NavBar.test.jsx                   # NEW (or extended): renders RefreshButton in trailing-actions
    │   │                                     #   only when RefreshContext has a published value
    │   └── ProtectedRoute.test.jsx           # NEW (or extended, if it exists under another name)
    └── integration/
        ├── main_menu_refresh.test.jsx        # NEW
        ├── admin_accounts_refresh.test.jsx   # NEW
        ├── main_menu_permissions_refresh.test.jsx  # NEW (added 2026-08-31): permission-revoked-between-
        │                                             #   load-and-refresh scenario (FR-011, spec.md Edge Cases)
        └── reload_resilience.test.jsx        # NEW: simulates a hard reload mid-session on a nested route
```

## Post-Design Constitution Check

*Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md).*

No new violations surfaced during design.

- **Principle IV (YAGNI)**: `data-model.md` deliberately models refresh/dirty state as ephemeral client state, not a persisted entity — confirmed no Cosmos DB or backend change is warranted anywhere in Phase 1 design. Still ✓ MET.
- **Principle XI**: Updated 2026-08-30 — `contracts/refresh-control.md` now records the product owner's already-updated prototypes (ghost button, Lucide `refresh-cw`, nav/title-bar placement) as the agreed design, rather than a proposal awaiting agreement. ✓ MET. **Updated 2026-08-31**: `022-persistent-nav-redesign-done` has since merged, so the mount point exists in code (`NavBar.jsx`'s `trailing-actions` slot); the remaining wiring question (how a page's refresh state reaches that sibling-rendered slot) is resolved via `RefreshContext` — see Constraints and Project Structure above. Still ✓ MET.

Constitution Check gate: **PASS**. Proceed to `/speckit-tasks`.
