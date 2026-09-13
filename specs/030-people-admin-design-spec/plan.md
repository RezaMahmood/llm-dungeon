# Implementation Plan: People (Admin) Screen Design-Spec Conformance

**Branch**: `030-people-admin-design-spec` | **Date**: 2026-09-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/030-people-admin-design-spec/spec.md`

## Summary

Bring the existing People screen (`AdminAccountsPage`/`AccountList`/`AccountForm`, delivered
by `014-account-listing`/`003-account-provisioning-done`) into conformance with the canonical
`specs/designs/05-admin-users.html`/`05-admin-users-spec.md` reference issue #333 attaches: a
full-bleed, no-page-scroll shell, a `PEOPLE` kicker + account-count heading, a two-column grid
(accounts table left, add-account panel right), a table with Microsoft account / Role / Status
/ Added / Remove columns, and an "Add someone" panel styled as an oversized-numeral card. The
issue's updated `styles.css` also centralizes a shared button-interaction language
(`.btn-primary`/`.btn-secondary`/`.btn-ghost`/`.nav a`) that this feature vendors into the
app's token layer, which visually affects buttons on every screen, per the issue's own
description. No gameplay, story, or session behavior changes; the only backend change is
serializing the already-stored `dateAdded` field on the accounts list response (FR-008).

Per spec.md's *Scope note*, the design's separate "Name" column and third Status state
("Signed out · {relative time}") are not implemented — the backend has no display-name field
and no live session/presence tracking, and this feature does not invent either. Both are
recorded as Assumptions and as explicit exceptions below.

## Technical Context

**Language/Version**: Python 3.12 (backend, Azure Functions), Node.js 22 LTS / React 19
(frontend) — per constitution Principle III, unchanged by this feature.

**Primary Dependencies**: Frontend — React, axios (`src/frontend/src/services/
accountService.js`), the existing `RefreshContext`/`useRefreshable` plumbing
(`019-spa-refresh-button`) `AdminAccountsPage` already uses. Backend — no new dependency;
`list_accounts` already reads `ProvisionedAccountEntry.dateAdded` from Cosmos, it is only not
yet serialized in `_account_summary`.

**Storage**: No schema change. `dateAdded` (FR-008) already exists on every
`ProvisionedAccountEntry` document in `PROVISIONED_ACCOUNTS_CONTAINER`
(`003-account-provisioning-done`); this feature adds it to the JSON the list endpoint returns.

**Testing**: `vitest`/React Testing Library (`src/frontend/tests`) for the restyle and new
Status/Added rendering; `pytest` (`src/backend/tests`) for the one endpoint-shape change.

**Target Platform**: Browser (React SPA) behind Azure Static Web Apps — unchanged.

**Project Type**: Web application (frontend + backend); this feature is frontend-led with one
small backend serialization change.

**Performance Goals**: No new goal. Table rendering at 20+ rows (SC-002) must not visibly lag
versus today.

**Constraints**: Layout/scroll contract (constitution "Layout and scroll contract" #1): the
shell has no page-level scroll at desktop/tablet widths. Design tokens only, from the app's
vendored layer `src/frontend/src/styles/designTokens.css` (source: `specs/designs/
styles.css`) — no literal hex/pixel/font value a token already covers (constitution "UI
Design System Requirements").

**Scale/Scope**: Three existing frontend components restyled (`AdminAccountsPage`,
`AccountList`, `AccountForm`), one page-scoped stylesheet added, one shared button-language
block added to `designTokens.css` (affects every screen's buttons, per the issue), one backend
serialization field added (`_account_summary`), and the three design artifacts issue #333
attaches vendored into `specs/designs/`. No new screens, no new routes, no new Cosmos
container.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing** — PASS (planned). Every conformance gap closed (grid
  layout, Status two-state rendering, Added column, restyled add-account panel, shared button
  states) gets its own test in `tests/components/AccountList.test.jsx` /
  `AccountForm.test.jsx` / `tests/integration/admin_accounts*.test.jsx`, alongside the current
  tests for those files, which must keep passing (updated only where they assert the exact
  `_account_summary` shape FR-008 extends — FR-013).
- **II. Secure-by-Default Access** — PASS. No new endpoint or route; `/admin/accounts` stays
  behind `ProtectedRoute`/`authorize_admin` exactly as today. `dateAdded` is an
  administrator-only-visible operational timestamp, not new PII (Principle X — see below).
- **III. Defined Technology Stack** — PASS. No new language, framework, or hosting.
- **IV. Simplicity Over Premature Scale** — PASS. Reuses the existing `listAccounts`/
  `useRefreshable`/`RefreshContext` plumbing; the backend change is one field added to an
  existing serializer, not a new query or index.
- **VIII. UI Design System & Accessibility Compliance** — PASS (planned, verified at
  implementation). Moves the page's remaining inline styles into a page-scoped stylesheet
  (`AdminAccounts.css`, matching the `Home.css`/`Play.css` precedent) and vendors the
  canonical `styles.css`'s new shared button block into `designTokens.css` so every screen's
  buttons — not just this one — pick up the visible-border/hover/pressed treatment FR-012
  requires. Role tags switch to the design's `.tag-outline`/`.tag-accent` pairing (already
  design-system classes, not new ones). Status dots are square (zero corner radius, rule 1)
  and never rely on color alone — the text label always carries the meaning (rule 4, Status
  column §6.1 of the design spec).
- **X. PII Protection by Design** — PASS. `dateAdded` (FR-008) is an operational timestamp
  already stored and already visible to administrators via the add-account response; exposing
  it on the list response adds no new PII surface. The two omitted design fields (a personal
  Name, and a presence/"last seen" signal) are exactly the kind of surface Principle X and the
  *Scope note* together caution against manufacturing — this feature's refusal to fabricate
  them is a PASS, not a gap.
- **XII. Right-Sized Scope** — PASS. No new infrastructure, no new persistent environment.
- **Layout and scroll contract** — PASS. Rule 1 (no page-level scroll at desktop/tablet) is
  satisfied by the design's `height:100vh; overflow:hidden` shell with the content area as the
  sole scroll container; the People screen is not the play surface, so rules 2–3 do not apply.
  Rule 4 (320px usability) is satisfied by the design's `auto-fit` grid, which already
  collapses to one column well above that floor.
- **Screen contracts** — PASS with two named, spec.md-documented exceptions. The constitution's
  "Administrator — people" entry ("add a Player or Administrator by email; existing accounts
  list their roles and are removed one at a time behind a confirmation dialog") is fully met.
  The two exceptions are additions the *canonical mockup* introduces beyond that constitution
  text (a Name column, a three-state Status), not requirements this feature fails to meet —
  see spec.md's *Scope note* and Assumptions.

**Complexity Tracking**: No violation requires justification — the two documented exceptions
are scope reductions against the mockup (not against the constitution's own screen-contract
text), matching the same pattern `029-play-surface-design-spec` established for its hint
control.

**Post-Phase-1 re-check**: Phase 1 introduces one new response field (`dateAdded` on the list
endpoint) and no new entity, endpoint, or schema change. All gates above still hold after
design.

## Project Structure

### Documentation (this feature)

```text
specs/030-people-admin-design-spec/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── ui.md              # Phase 1 output — the People-screen UI contract + the one API field
└── tasks.md               # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
specs/designs/
├── 05-admin-users.html         # updated — issue #333's canonical mockup
├── 05-admin-users-spec.md      # NEW — issue #333's canonical written spec, vendored
├── styles.css                  # updated — issue #333's shared button-language block
└── README.md                   # updated — screen list + implementer notes for 05

src/backend/
├── api/admin/accounts.py       # _account_summary + dateAdded (FR-008)
└── tests/integration/
    └── test_admin_accounts_endpoint.py  # updated shape assertions + new dateAdded coverage

src/frontend/
├── src/
│   ├── styles/
│   │   └── designTokens.css     # + shared button-interaction block (border/hover/press),
│   │                            #   + .nav a underline states, vendored from styles.css
│   ├── components/Admin/
│   │   ├── AdminAccounts.css    # NEW — page-scoped structural rules (mirrors Home.css/Play.css):
│   │   │                        #   kicker, grid body, .status/.status-on/.status-off,
│   │   │                        #   add-account panel treatment
│   │   ├── AccountList.jsx      # + Added column, two-state Status (dot+label), .tag-outline/
│   │   │                        #   .tag-accent role tags, table/dialog classes only (no inline)
│   │   └── AccountForm.jsx      # restyled to the "Add someone" panel: .ovnum, field
│   │                            #   descriptions, .btn-primary .btn-block submit
│   └── pages/
│       └── AdminAccountsPage.jsx  # full-bleed shell, PEOPLE kicker + count heading,
│                                #   two-column grid wiring AccountList/AccountForm
└── tests/
    ├── components/
    │   ├── AccountList.test.jsx   # + Status/Added/role-tag assertions
    │   └── AccountForm.test.jsx   # + restyled-panel assertions (role descriptions, .btn-block)
    └── integration/
        ├── admin_accounts.test.jsx          # + grid-layout / heading-count assertions
        └── admin_accounts_refresh.test.jsx  # regression only — Refresh already wired
```

**Structure Decision**: Existing web-application layout (`src/backend`, `src/frontend`) is
kept as-is; this feature touches only the frontend's existing `Admin` account components and
the shared token layer, plus one backend serializer field, following the same
page-scoped-stylesheet pattern `028-home-page-redesign`/`029-play-surface-design-spec`
established with `Home.css`/`Play.css`. No new directories.
