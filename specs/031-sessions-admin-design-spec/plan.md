# Implementation Plan: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Branch**: `031-sessions-admin-design-spec` | **Date**: 2026-09-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/031-sessions-admin-design-spec/spec.md`

## Summary

Two pieces of work that issue #335 puts in one screen.

**The restyle.** `AdminSessionsPage` (026-token-usage) is a `maxWidth: 1020px` block with an
`<h1>`, an unstyled `.table`, and inline styles. It becomes the canonical
`specs/designs/08-admin-sessions.html`/`08-admin-sessions-spec.md` screen: a full-bleed
no-page-scroll shell sharing the People screen's structure, a `SESSIONS` kicker over a computed
`{n} sessions across {m} stories` heading, and a table with a monospace wrapping session id, a
right-aligned tabular-nums token column, an italic `(deleted story)` label, a ghost per-row
Delete, a caption, and an empty state. The shared button language and dialog primitives landed
with `030-people-admin-design-spec`, so this screen declares no button styling of its own.

**The deletion.** New admin-only `DELETE /api/manage/sessions/{sessionId}`, resolving player
and test-play sessions from one id (research.md Decision 1), behind the existing
`ConfirmDeleteDialog`. `026-token-usage` FR-016 ("the Sessions page MUST be read-only") is
superseded, and the constitution's **Administrator — sessions** screen contract is amended in
this feature's own PR (research.md Decision 10) — the screen may not ship ahead of it.

**The correction the deletion forces.** `backend/api/game/sessions.py` currently catches
`SessionNotFoundError` and `AdventureNotFoundError` together and answers both with
`story_deleted`. Once an administrator can delete a session under a live story, that tells the
player their story was deleted when it was not. The two are split, `session_removed` is
introduced, and it drives the bump: `PlayPage` → `GamePage` → `navigate("/menu")` → a
dismissible dialog on Home (spec FR-012/FR-012a, research.md Decisions 3 and 5).

## Technical Context

**Language/Version**: Python 3.12 (backend, Azure Functions), Node.js 22 LTS / React 19
(frontend) — Principle III, unchanged.

**Primary Dependencies**: No new dependency, frontend or backend. Reuses `SessionOverviewService`,
`PlaySessionService`, `TestPlaySessionService`, `authorize_admin`, `ConfirmDeleteDialog`,
`RefreshContext`/`usePublishRefresh`, and react-router's route state.

**Storage**: No schema change, no new container, no new field. One new operation (delete) over
two existing entities — see [data-model.md](./data-model.md).

**Testing**: `pytest` (`src/backend/tests`) for the delete path, the admin endpoint, and the
`session_removed` split; `vitest`/RTL (`src/frontend/tests`) for the restyle, the delete flow,
and the bump.

**Target Platform**: Browser (React SPA) behind Azure Static Web Apps — unchanged.

**Project Type**: Web application (frontend + backend). Unlike 030, this one is genuinely
full-stack: a new endpoint, two new service methods, and a corrected error contract on four
existing player endpoints.

**Performance Goals**: None new. The delete is a point-delete on a `/id`-partitioned container.

**Constraints**: No page-level scroll at desktop/tablet (constitution "Layout and scroll
contract" #1). Tokens only, from `src/frontend/src/styles/designTokens.css`. Server-side
authorization on the new endpoint (Principle II) — a client-side check is never sufficient for a
destructive operation.

**Scale/Scope**: One page rewritten, one page-scoped stylesheet added, one service method added
to each of three backend services, one endpoint added, four existing handlers corrected, one new
frontend service call, and the bump wired through three existing pages. Plus the two governance
edits (constitution screen contract, `specs/designs/README.md`) and the vendored design files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing** — PASS (planned). Every new behaviour gets a test that
  exercises it rather than its presence: the delete resolving across both containers and 404ing
  when neither holds the id; the admin endpoint refusing a non-admin; each of the four player
  endpoints returning `session_removed` for a missing session **and still returning
  `story_deleted` for a missing story** (the regression that matters most — quickstart.md step
  17); the heading's singularisation and deleted-story exclusion; the failure and
  already-deleted delete paths; and the bump reached from all four player actions.
- **II. Secure-by-Default Access** — PASS. The new endpoint is behind `authorize_admin`, the
  same gate the existing `GET /api/manage/sessions` uses, enforced server-side and independently
  of the UI (spec FR-010). The two new service methods are named `…_as_administrator` precisely
  so an owner-checked path can never be reached by passing a falsy owner (research.md
  Decision 2).
- **III. Defined Technology Stack** — PASS. No new language, framework, or hosting.
- **IV. Simplicity Over Premature Scale** — PASS, and actively enforced: the user's decision of
  2026-09-13 rules out both polling and a push channel for detecting a deleted session
  (spec *Assumptions*). Detection is on the player's next action, which needs no new
  infrastructure at all.
- **VI. Observability & AI Cost Transparency** — PASS. Deletion removes a session's own
  `totalTokens` but never touches the per-LLM-call telemetry Principle VI requires, and never
  decrements `Story.totalTokens` (spec FR-009). The screen's caption is worded to be true of
  what actually survives (contracts/ui.md §3) rather than repeating the mockup's claim of a
  usage record that does not exist.
- **VIII. UI Design System & Accessibility Compliance** — PASS (planned, verified at
  implementation). Page structure goes in `AdminSessions.css` alongside `AdminAccounts.css`;
  every visual value comes from `designTokens.css`; the delete dialog is the existing
  `ConfirmDeleteDialog`, not a fourth copy. Delete is a ghost button, not a red one — accent
  stays reserved (visual rule 4). `(deleted story)` is a text label, so meaning is never carried
  by colour alone. Real `<table>`/`<th scope>`/`<button>`, and the row action's accessible name
  distinguishes rows rather than being a bare icon.
- **X. PII Protection by Design** — PASS, with one thing to watch: the delete confirmation body
  quotes the session's owning account, which is PII. That is a rendered, administrator-only UI
  string inside the access-controlled app — the same surface the table already shows — and it
  MUST NOT be carried into logs, telemetry, commit messages, the PR description, or this spec
  folder. The vendored mockup's sample addresses are synthetic (`@company.internal`).
- **XII. Right-Sized Scope** — PASS. No new infrastructure, no new environment, no new role or
  permission tier — deletion rides on the existing Administrator role.
- **XIV. Spec Artifacts and Code Stay Clean** — PASS. `026-token-usage` FR-016 is recorded as
  superseded in this spec's *Scope note* in one line, not narrated across both features.
- **Layout and scroll contract** — PASS. Rule 1 is satisfied by the fixed shell with the content
  area as the sole scroll container; rules 2–3 are play-surface-only. Rule 4 (320px) is
  satisfied by the design's wrapping cells, which is also why FR-017 forbids horizontal scroll.
- **Screen contracts** — **NO LONGER APPLICABLE.** Constitution v10.0.0 (issue #340) withdrew
  the Screen contracts section, so there is no **Administrator — sessions** contract to
  contradict, no traceability gate, and nothing for FR-021 (now withdrawn) to amend. The
  canonical design files and the delete affordance are stated by this spec alone. Supersedes:
  the v9.x contract read "no prototype screen" and "a read-only list", which this feature
  deliberately contradicted and amended as a required task.

**Complexity Tracking**: One deviation from the canonical mockup is recorded rather than
justified away — the confirmation dialog's buttons sit in a row (`ConfirmDeleteDialog`) rather
than stacked as the mockup draws them, because reimplementing a shared control to match one
static file is what Principle VIII forbids (research.md Decision 6, contracts/ui.md §5). The
caption rewording (contracts/ui.md §3) is the second and last documented deviation.

**Post-Phase-1 re-check**: Phase 1 added one endpoint, two service methods, one error code, and
no entity, field, container, or dependency. Every gate above still holds. The screen-contract
gate remains conditional on the amendment landing in this PR.

## Project Structure

### Documentation (this feature)

```text
specs/031-sessions-admin-design-spec/
├── plan.md               # This file
├── research.md           # Phase 0 output — 10 decisions
├── data-model.md         # Phase 1 output — no new entities; two new lifecycle transitions
├── quickstart.md         # Phase 1 output — automated gate + manual walkthrough
├── contracts/
│   ├── api.md            # Phase 1 output — the new endpoint + the session_removed correction
│   └── ui.md             # Phase 1 output — the screen contract + the two deviations
├── checklists/
│   └── requirements.md   # Spec quality checklist
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
.specify/memory/
└── constitution.md                     # AMEND — "Administrator — sessions" screen contract
                                        #   (FR-021): prototype reference + delete affordance

specs/designs/
├── 08-admin-sessions.html              # NEW — issue #335's canonical mockup, vendored
├── 08-admin-sessions-spec.md           # NEW — issue #335's canonical written spec, vendored
└── README.md                           # updated — screen list + implementer notes for 08

src/backend/
├── api/
│   ├── admin/sessions.py               # + delete_session handler (admin-only)
│   └── game/sessions.py                # split SessionNotFoundError from AdventureNotFoundError
│                                       #   across submit/resume/get; checkpoint 404 → session_removed
├── function_app.py                     # + DELETE manage/sessions/{sessionId} route
├── services/
│   ├── session_overview_service.py     # + delete_session(session_id): resolve across containers
│   ├── play_session_service.py         # + delete_session_as_administrator(session_id)
│   └── test_play_session_service.py    # + delete_session_as_administrator(session_id)
└── tests/
    ├── unit/
    │   ├── test_session_overview_service.py    # + delete resolution / not-found
    │   ├── test_play_session_service.py        # + admin delete; owner-checked paths unchanged
    │   └── test_test_play_session_service.py   # + admin delete; lastTestPlayedAt untouched
    └── integration/
        ├── test_admin_sessions_endpoint.py     # + DELETE 200/404/403/401
        └── test_game_sessions_endpoint.py      # + session_removed vs story_deleted, all 4 handlers

src/frontend/
├── src/
│   ├── components/Admin/
│   │   ├── AdminSessions.css           # NEW — page-scoped structure (kicker, shell, mono id
│   │   │                               #   cell, numeric column, deleted label, caption)
│   │   ├── SessionsTable.jsx           # NEW — the table + per-row delete action
│   │   └── SessionDeleteAction.jsx     # NEW — ghost Delete + ConfirmDeleteDialog wiring
│   ├── components/Home/
│   │   └── SessionRemovedDialog.jsx    # NEW — the bump's dismissible dialog
│   ├── pages/
│   │   ├── AdminSessionsPage.jsx       # rewritten — shell, kicker, computed heading, empty state
│   │   ├── PlayPage.jsx                # + onSessionRemoved on the 4 action paths
│   │   ├── GamePage.jsx                # + navigate("/menu", { state: { sessionRemoved } })
│   │   └── HomePage.jsx                # + consume one-shot route state, render the dialog
│   └── services/
│       └── sessionService.js           # + deleteSession(token, sessionId)
└── tests/
    ├── components/
    │   └── SessionsTable.test.jsx      # NEW — columns, formatting, deleted label, empty state
    ├── Play/PlayPage.test.jsx          # + session_removed leaves rather than noticing in place
    └── integration/
        ├── admin_sessions_list.test.jsx     # updated — restyled shell, heading counts
        ├── admin_sessions_delete.test.jsx   # NEW — confirm/cancel/success/failure/404
        └── home_session_removed.test.jsx    # NEW — the bump end to end
```

**Structure Decision**: The existing web-application layout is kept. The Sessions page follows
the component split 030 established for People (a page owning the shell and heading, a table
component, a delete-action component, one page-scoped stylesheet) rather than keeping everything
in one page file, because the delete action carries dialog state that does not belong in the
page. `SessionRemovedDialog` lives under `components/Home/` because Home is where it renders,
next to `SessionDeleteAction.jsx`, the player's own equivalent.

**Naming collision to avoid**: `components/Home/SessionDeleteAction.jsx` already exists — the
player deleting their own saved game. The new admin one is a different component under
`components/Admin/`. Two files of the same basename in different folders is the existing
convention here (`AccountList`/`AccountForm` sit under `Admin/` likewise), but the import lines
must be read carefully during implementation.
</content>
