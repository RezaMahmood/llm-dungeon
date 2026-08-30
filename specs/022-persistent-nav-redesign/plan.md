# Implementation Plan: Persistent Navigation & Design Refresh

**Branch**: `022-persistent-nav-redesign` | **Date**: 2026-08-30 | **Spec**: `specs/022-persistent-nav-redesign/spec.md`

**Input**: Feature specification from `/specs/022-persistent-nav-redesign/spec.md`

## Summary

Add one shared, capability-driven persistent top nav bar (a compact title bar on the
story-play screen) and restyle the app's five primary screens onto the vendored
Modernist design system, replacing each screen's current ad hoc header/styling.
Concretely: a new `AuthenticatedLayout` component wraps every `ProtectedRoute`-guarded
screen, rendering `NavBar` (or `TitleBar` on `/game`) driven by the existing
`useCapabilities()` hook (`hasPlayer`/`hasAdministrator`), with `aria-current` marking
the active route; `MainMenu.jsx`, `AdminAccountsPage.jsx`, `AdminStoryWizardPage.jsx`,
and `LoginScreen.jsx` are restyled in place to match `specs/designs/02, 04, 05, 01`
respectively, with all functional behavior (account remove/confirm, wizard step
save/autosave, capability checks) unchanged.

**Cross-feature note (read before implementing)**: this feature is a hard, in-repo
dependency for `019-spa-refresh-button`'s User Story 1 mounting tasks (019's
`RefreshButton` is designed to render inside the nav bar this feature builds) and
shares two files with 019's other changes (`ProtectedRoute.jsx`, and the three
screens both features touch). It also uncovers a real discrepancy between 019's
planning docs and the actual current design mockups — see "Cross-Feature
Dependencies & Sequencing (022 ↔ 019)" below. Read that section before starting
`/speckit-tasks`.

## Technical Context

**Language/Version**: JavaScript (ES2022) + React 18 via Vite (existing, `src/frontend/`)

**Primary Dependencies** (all existing, no additions):
- `react-router-dom` v6 — `App.jsx` routing table, `<Link>`/`useLocation` for
  nav-item active-state detection
- `@azure/msal-browser` / `@azure/msal-react` — `AuthProvider.jsx`, `ProtectedRoute.jsx`,
  `useCapabilities.js` (already wraps `GET /api/auth/me`)
- The vendored design-token stylesheet `src/frontend/src/styles/designTokens.css`
  (copied from `specs/designs/styles.css`, per Constitution Principle VIII) — already
  imported globally via `index.css`, and already defines unused `.nav`/`.nav-brand`
  classes (`designTokens.css:216-227`) this feature is the first to consume

**Storage**: N/A — no persisted entity is introduced; capability state is already
fetched by `useCapabilities()` and nav visibility is derived from it at render time

**Testing**: Vitest + React Testing Library, `src/frontend/tests/{components,hooks,integration}`
(existing convention, `vite.config.js` + `tests/setup.js`)

**Target Platform**: Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application — frontend-only change to `src/frontend/`; no
`src/backend/` or `infrastructure/terraform/` changes (no new/changed API surface —
`GET /api/auth/me` already returns the capabilities this feature reads)

**Performance Goals**: N/A — no throughput/latency target specified (Principle IV);
this is a rendering/styling change with no new network calls

**Constraints**:
- Every color/font/spacing/radius value MUST come from `designTokens.css`; no new
  hex literals or magic pixel values (Principle VIII) — the existing per-screen inline
  `style={{ padding: "var(--space-6)" }}` pattern already does this and continues.
- The nav bar's underlying markup/classes (`.nav`, `.nav-brand`, `.btn`, `.tag`, `.hr`)
  MUST come from `designTokens.css` unmodified — this feature is the first to render
  them, not the first to define them.
- FR-011/FR-012 (preserve People's remove/confirm behavior; no functional behavior
  change anywhere) constrain this to a rendering/layout refactor of
  `AdminAccountsPage.jsx`, `AdminStoryWizardPage.jsx`, and `MainMenu.jsx` — their data
  fetching, mutation, and validation logic must not change.
- **Open design gap requiring resolution before/alongside `/speckit-tasks`**: the
  actual current mockups (`specs/designs/02-story-select.html`, `04-admin-wizard.html`,
  `05-admin-users.html`) contain the shared `.nav` bar with **no Refresh control** in
  it — only `specs/designs/03-play.html`'s title bar has one. This contradicts
  `019-spa-refresh-button`'s plan.md/research.md/tasks.md, which assert (citing commit
  `4a43123` / PR #79) that the Refresh button was added to the nav bar on `02`, `04`,
  and `05` too, and that `README.md` documents it under a "## Refresh" section — neither
  is true of the files on this branch (verified 2026-08-30; only `03-play.html` and its
  title-bar entry exist). See "Cross-Feature Dependencies" below for the resolution
  this plan recommends.

**Scale/Scope**: Applies to all five primary screens named in FR-010. Two of the
routes this feature restyles a *header* for — `/menu` (mapped loosely to the "hub"
role `02-story-select.html` plays in the mockups) and `/game` — are themselves still
functional placeholders (`MainMenu.jsx` has no real story list yet; `GamePage.jsx`
renders "Game features loading…", per `019-spa-refresh-button`'s plan and
`008-core-gameplay`/`004-story-creation`'s own scope). This feature restyles what
exists today (the hub menu, the placeholder game landing) and builds the nav/title
bar correctly for when those screens gain real content later — it does not invent a
new story-list UI; that remains `004-story-creation`'s and `008-core-gameplay`'s scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — Each FR maps to a distinct, testable behavior: nav item
visibility per capability combination (FR-002/003/008), `aria-current` on the active
route (FR-007), presence/absence of the nav bar on `/login` and `/game` (FR-006/009),
wizard-progress survival across a nav click (FR-005), and People's preserved
remove/confirm flow (FR-011). Phase 1 contracts define exactly what these tests assert.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — Nav-item visibility is a rendering convenience layered on top of
capabilities `useCapabilities()` already fetches from the server; it grants no new
client-side-only access. `ProtectedRoute.jsx`'s existing server-verified capability
gate is unchanged in substance — this feature only adds a layout wrapper around what
`ProtectedRoute` already renders, not a new authorization decision point.

### Principle III – Defined Technology Stack
**Status**: ✓ MET — No new language, framework, or hosting model; no new dependency.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — One `NavBar`/`TitleBar`/`AuthenticatedLayout` set, reusing the
design system's already-vendored, already-defined `.nav` classes; no new
state-management library, no client-side routing beyond existing `react-router-dom`
usage, no new permission model (reuses `hasPlayer`/`hasAdministrator` as-is).

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing Vitest suite already wired
into CI (`test.yml`); no new CI configuration needed.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: N/A — No LLM calls, no LLM-adjacent surface.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: N/A — No new Azure resource dependency or inter-resource communication.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET, with the open gap noted above — This feature is precisely what
Principle VIII exists to enforce: it retires per-screen ad hoc styling (`MainMenu.css`,
inline centered layouts, an unstyled `AdminAccountsPage.jsx`) in favor of the
already-vendored token layer and its `.nav`/`.btn`/`.tag`/`.hr` classes, with zero new
hex/magic-pixel values. All four interaction states (hover/pressed/focus/disabled) on
nav links and buttons come from the shared `.btn`/`.nav` styling already defined in
`designTokens.css`, not per-instance overrides. **Exception requested**: the
"Player view" / "Admin" cross-role links (FR-002/FR-003, spec User Story 3) are new
interactive elements not present in any existing screen's current implementation —
they are, however, already fully specified in the merged mockups (`04-admin-wizard.html:27`,
`05-admin-users.html:26`, and player-side per spec FR-003), so no new design judgment
is required, only implementation of an already-agreed control.

### Principle IX – User-Verified Acceptance Before Completion (NON-NEGOTIABLE)
**Status**: Deferred to tasks.md — per constitution, `tasks.md` must end with an
explicit final acceptance task verified by the requesting user/product owner against
the real deployed environment, covering all five restyled screens and both
single-capability and dual-capability accounts (User Stories 1–4).

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: N/A — No new data is stored, logged, or displayed; the nav bar shows the
already-displayed signed-in user's display name (`useCapabilities`/`/api/auth/me`
already returns this data to the client; this feature does not add new PII exposure
beyond what already renders as the account's own logged-in identity).

### Principle XI – UI Design Pre-Agreement Before Implementation (NON-NEGOTIABLE)
**Status**: ⚠ PARTIALLY MET — CONDITIONAL, gate for `/speckit-tasks`. Four of five
screens (`01-login.html`, `02-story-select.html`, `04-admin-wizard.html`,
`05-admin-users.html`) and the nav bar's own structure/link sets are fully specified
in the merged `specs/designs/` mockups and `specs/022-persistent-nav-redesign/spec.md`
— sufficient to implement without further design judgment. **However**: the Refresh
control discrepancy above means the nav bar's *complete, final* visual contract is
not settled — `019-spa-refresh-button`'s existing tasks.md (T001, T009–T011) already
assumes a Refresh slot exists in this feature's nav bar on `02`/`04`/`05`, but the
actual mockups this feature must build from do not show one. **`tasks.md` MUST include
an explicit UI design agreement/sign-off task**, per Principle XI, that resolves this
before any nav-bar implementation task: either (a) the product owner updates
`02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`, and
`README.md` to actually add the Refresh control (making 019's docs accurate and this
feature's nav bar the final design), or (b) the product owner confirms no Refresh
control belongs in the nav bar for those three screens (leaving it only on
`03-play.html`'s title bar, and 019's task docs are corrected instead). This plan
does not decide between (a)/(b) — that is exactly what Principle XI's human gate is
for — but recommends building `NavBar`'s right-aligned button cluster (before "Sign
out") as an ordinary flex row rather than a fixed two-slot layout, so that either
outcome is a small, non-restructuring addition.

No unjustified constitution violations — Complexity Tracking table is not needed.

## Cross-Feature Dependencies & Sequencing (022 ↔ 019)

`019-spa-refresh-button` (Draft spec.md → plan.md/tasks.md already generated,
per commit `4d501e0`) and this feature were investigated together per this session's
request. Findings:

1. **Physical, one-directional dependency, no functional overlap.** 019's FR-001–FR-011
   never mention navigation; this feature's FR-001–FR-012 never mention refresh. The
   only coupling is *where 019's `RefreshButton` renders* — inside the nav bar / title
   bar this feature builds. 019's own tasks.md already reaches this conclusion
   independently (`specs/019-spa-refresh-button/tasks.md` lines 129–145) and blocks its
   T009–T011 (mounting `RefreshButton` into `MainMenu.jsx`/`AdminAccountsPage.jsx`/
   `AdminStoryWizardPage.jsx`) pending this feature landing, while proceeding
   immediately with 019's US2 (browser-reload resilience) and US3 (unsaved-changes
   warning), which touch none of this feature's files.

2. **Design-doc discrepancy (new finding, not previously surfaced in 019's docs).**
   019's plan.md, research.md §7, and tasks.md T001/T009 all state that the product
   owner already added a Refresh control to the nav bar on `02-story-select.html`,
   `04-admin-wizard.html`, and `05-admin-users.html` (citing commit `4a43123`, PR #79),
   with `README.md` documenting it under "## Refresh". **Verified against the actual
   files on this branch (descended from `main` at commit `4d501e0`): this is only true
   of `03-play.html`'s title bar.** `02`, `04`, `05`, and `README.md` show no Refresh
   control at all. This plan's Constitution Check (Principle XI, above) turns this into
   an explicit sign-off task for `/speckit-tasks` rather than silently building the nav
   bar to match either feature's assumption.

3. **File-level overlap requiring sequencing, not just a shared component.** Both
   features modify:
   - `ProtectedRoute.jsx` — 019 changes *when* it judges `isAuthenticated` (gates on
     MSAL's `inProgress`/`InteractionStatus` first); this feature changes *what* it
     renders (wraps `children` in the new `AuthenticatedLayout`/nav). These are
     additive, non-conflicting changes in isolation, but whichever feature's PR merges
     second will need to rebase onto the first's version of this file.
   - `MainMenu.jsx`, `AdminAccountsPage.jsx`, `AdminStoryWizardPage.jsx` — this feature
     restyles each screen's header/layout; 019 (once unblocked) mounts a button inside
     the nav bar this feature puts there. Recommend this feature lands its restyle of
     these three files *before* 019's T009–T011 are attempted, exactly as 019's own
     tasks.md already recommends, so 019 mounts into a finished nav bar rather than two
     branches racing to restructure the same headers.

4. **Recommended sequencing for `/speckit-tasks` (this feature) and for re-checking
   019's tasks.md once this feature merges**:
   - This feature's tasks should implement `NavBar`/`TitleBar`/`AuthenticatedLayout`
     and all five screens' restyle end-to-end, merging as a complete, independently
     shippable unit (its own FRs have no dependency on 019).
   - Before this feature's `ProtectedRoute.jsx` and three-screen changes are
     implemented, resolve the Principle XI Refresh-slot sign-off (Constitution Check
     above) — cheaper to build the final nav-bar markup once than to restructure it
     twice.
   - Once this feature merges, `019-spa-refresh-button`'s tasks.md T009–T011 (and its
     `ProtectedRoute.jsx`-touching US2 tasks, if not already merged) should be
     rebased/re-verified against this feature's actual merged `AuthenticatedLayout`
     and nav-bar markup, and its own docs' Refresh-slot claims corrected per finding 2.
   - No action is needed on 019's US2/US3 tasks now — they are independent and should
     not wait on this feature.

## Project Structure

### Documentation (this feature)

```text
specs/022-persistent-nav-redesign/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   ├── nav-bar.md
│   └── screen-restyle.md
└── tasks.md              # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout, frontend-only
(`src/frontend/`, established by `002-login-and-access-control`). No `src/backend/`
or `infrastructure/terraform/` changes.

```text
src/frontend/src/
├── components/
│   ├── Layout/
│   │   ├── AuthenticatedLayout.jsx   # NEW: renders NavBar (or TitleBar on /game) + children;
│   │   │                             #   reads route via useLocation to pick TitleBar vs NavBar
│   │   │                             #   and to compute the active nav item (FR-006/FR-007)
│   │   ├── NavBar.jsx                # NEW: `.nav`/`.nav-brand` markup from designTokens.css;
│   │   │                             #   admin/player link sets + "Player view"/"Admin" cross-links
│   │   │                             #   driven by useCapabilities() (FR-002/003/004/008/009)
│   │   └── TitleBar.jsx              # NEW: compact story-play title bar (brand mark, story title,
│   │                                 #   return-to-select, pause/exit) replacing NavBar on /game (FR-006)
│   ├── Auth/
│   │   └── ProtectedRoute.jsx        # MODIFY: wrap children in <AuthenticatedLayout> —
│   │                                 #   coordinate with 019's separate MSAL-timing change (see above)
│   ├── Menu/
│   │   ├── MainMenu.jsx              # MODIFY: remove ad hoc <h1>/logout header (now in NavBar),
│   │   │                             #   restyle body per 02-story-select.html's design language
│   │   └── MainMenu.css              # MODIFY/REMOVE: superseded by design-token classes
│   ├── Login/
│   │   └── LoginScreen.jsx           # MODIFY: confirm/complete alignment with 01-login.html
│   │                                 #   (largely already token-based per research.md)
│   └── Common/
│       └── (unchanged)
├── pages/
│   ├── AdminAccountsPage.jsx         # MODIFY: adopt NavBar via AuthenticatedLayout; restyle
│   │                                 #   per 05-admin-users.html; keep AccountForm/AccountList
│   │                                 #   components and their remove/confirm behavior unchanged (FR-011)
│   ├── AdminStoryWizardPage.jsx      # MODIFY: adopt NavBar via AuthenticatedLayout; restyle
│   │                                 #   step-tab row per 04-admin-wizard.html; wizard save/autosave
│   │                                 #   logic and activeStep state untouched (FR-005/FR-012)
│   ├── AdminPage.jsx                 # MODIFY: minor restyle only (still a placeholder pending
│   │                                 #   005-story-publishing/012-story-editing-and-review)
│   └── GamePage.jsx                  # MODIFY: render under TitleBar instead of NavBar (FR-006);
│                                     #   remains a content placeholder pending 008-core-gameplay
└── App.jsx                            # Unchanged routing table; ProtectedRoute now renders the
                                      # shared layout for every guarded route
```

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No unjustified violations. Principle XI's status above is conditional/gating, not a
violation requiring a complexity-tracking entry — it is resolved by a sign-off task
in `tasks.md`, per the constitution's own mechanism for this exact situation.
