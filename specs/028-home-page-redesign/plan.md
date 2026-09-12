# Implementation Plan: Player Home Page Redesign

**Branch**: `028-home-page-redesign` | **Date**: 2026-09-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/028-home-page-redesign/spec.md`

## Summary

Replace the current post-login `/menu` hub (a two-button "Start or Continue Game" /
"Administration" menu) with a single Home page matching `specs/designs/07-home.html`: a nav
bar, a welcome band, and a two-column body listing the player's in-progress sessions
(Resume, Delete) and not-yet-started published stories (Play). `GamePage`'s own duplicate
in-progress/catalogue list is removed; `GamePage` becomes the adventure-setup flow only,
entered from Home's Play/Resume. A new backend capability lets a player delete their own
saved session (soft requirement: only the session, never the story).

## Technical Context

**Language/Version**: Python 3.12 (backend, Azure Functions), Node.js 22 LTS / React 18
(frontend) — per constitution Principle III, unchanged by this feature.

**Primary Dependencies**: Backend: `azure-functions`, `azure-cosmos`. Frontend: React Router,
axios (`src/frontend/src/services/gameService.js`), MSAL (`@azure/msal-react`). No new
dependency is introduced.

**Storage**: Azure Cosmos DB — `PLAY_SESSIONS_CONTAINER` (existing `PlaySession` documents,
partitioned by `id`) and the `STORIES_CONTAINER` (existing `Story` documents), both already
read by `PlaySessionService`/`StoryService`. No schema change; deletion removes an existing
document, it does not add fields.

**Testing**: `pytest` (backend, `src/backend/tests`), `vitest`/RTL (frontend,
`src/frontend/tests`) — both already wired into CI per Principle I.

**Target Platform**: Azure Functions (backend) behind Azure Static Web Apps / browser
(frontend) — unchanged.

**Project Type**: Web application (frontend + backend), matching the existing repo layout.

**Performance Goals**: No new goal beyond existing hot-path expectations; Home's two lists
reuse `list_player_sessions` (already optimized as a hot path per its own docstring) and
`list_published_summaries`.

**Constraints**: Layout/scroll contract (Article V / constitution "Layout and scroll
contract"): no page-level scroll on desktop/tablet; only the two columns scroll
independently. Design tokens only from `specs/designs/styles.css` — no literal hex/font
values (constitution "UI Design System Requirements").

**Scale/Scope**: One redesigned frontend page (replacing `MainMenu`), one route removal
(the setup flow's own story-select UI), one new backend delete endpoint + service method,
one new frontend service call, and one new plain admin-authored `blurb` field threaded
through `Story`/`StoryDraft`, the authoring wizard, the configuration file schema, and the
player-facing story projection (resolved via user clarification: the mockup's "Ready to
play" row requires a short blurb that has no existing backend field — see research.md
Decision 5). No new screens beyond the one design-reference addition.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing** — PASS (planned). New/changed behavior (Home
  rendering, delete-session flow, GamePage narrowing) gets component/integration tests per
  existing patterns (`tests/components/MainMenu.test.jsx` → renamed/rewritten,
  `tests/integration/*`), and the new backend delete path gets a `pytest` unit + contract
  test alongside `play_session_service`'s existing tests.
- **II. Secure-by-Default Access** — PASS. Home sits behind the existing `ProtectedRoute`;
  the new delete endpoint goes through the same `authorize_player` middleware every other
  `game/sessions/*` route uses, and only ever deletes a session whose `playerId` matches the
  authenticated caller (never trusts a client-supplied owner).
- **III. Defined Technology Stack** — PASS. No new language/framework/hosting.
- **IV. Simplicity Over Premature Scale** — PASS. Reuses existing services
  (`PlaySessionService`, `StoryService`) and existing summary shapes; no new abstraction
  layer.
- **VIII. UI Design System & Accessibility Compliance** — PASS (planned, verified at
  implementation). Built from `specs/designs/styles.css` tokens only; keyboard operability,
  visible focus, and no color-only meaning are carried over from the design spec's own
  interaction rules (`specs/designs/07-home-spec.md` §8–9) and the constitution's
  accessibility section.
- **X. PII Protection by Design** — PASS. No new PII is introduced; the name/role chip
  already exists in `NavBar`.
- **XII. Right-Sized Scope** — PASS. One page, one new endpoint; no new infra.
- **Screen contracts (constitution "Screen contracts")** — REQUIRES AN AMENDMENT. The
  constitution currently names `specs/designs/02-story-select.html` as the sole "Adventure
  select" acceptance reference. This feature's plan updates that paragraph to point at the
  new `specs/designs/07-home.html` as the current acceptance reference for the
  in-progress/ready-to-play behavior, per the resolved clarification (spec.md). This is a
  **governance-document edit** (`.specify/memory/constitution.md`), which per this repo's
  own review-triage rules always requires the `ultra` code-review tier regardless of diff
  size — recorded here so the eventual PR description carries that tier, and flagged to the
  user since only a human merges governance changes.

No violation requires a Complexity Tracking entry — the constitution amendment is a
documentation update tracking an already-approved product change, not a principle violation.

**Post-Phase-1 re-check**: Decision 5 (research.md) adds one optional field (`blurb`) to two
existing documents (`Story`, `StoryDraft`). Cosmos DB is schemaless, so this is additive with
no migration and no risk to existing records — it does not trigger the "persisted data:
schema, migrations, or anything that can delete or rewrite existing records" blast-radius
row on its own; the `ultra` tier already applies via the constitution edit regardless. All
gates above still PASS after Phase 1 design.

## Project Structure

### Documentation (this feature)

```text
specs/028-home-page-redesign/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── api.md            # Phase 1 output — new/changed HTTP contract
└── tasks.md               # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
specs/designs/
├── 07-home.html              # NEW — vendored design reference (from issue #328's mockup)
└── README.md                  # updated: add 07 to the screen list + implementer notes

.specify/memory/constitution.md  # updated: "Adventure select" screen contract → 07-home.html

src/backend/
├── api/game/sessions.py        # + delete_session (DELETE /game/sessions/{sessionId})
├── function_app.py             # + route registration for the DELETE above
├── services/play_session_service.py  # + delete_player_session(session_id, player_id)
├── models/story.py              # + blurb: Optional[str] on Story
├── models/story_draft.py        # + blurb: Optional[str] on StoryDraft
├── services/story_draft_service.py  # + blurb in the PATCH-able draft field allowlist
├── services/story_service.py    # + blurb in list_published_summaries projection
├── services/story_config_file.py  # + blurb in export/import schema
└── tests/
    ├── api/game/test_sessions.py         # + delete endpoint tests
    ├── services/test_play_session_service.py  # + delete_player_session tests
    └── services/test_story_*.py            # + blurb round-trip tests (draft, publish, import)

src/frontend/
├── src/
│   ├── pages/
│   │   ├── HomePage.jsx        # NEW — replaces MainMenu as the /menu route element
│   │   └── GamePage.jsx        # narrowed: drops its own in-progress/catalogue list;
│   │                            #   keeps adventure-setup (character name/type) + PlayPage handoff
│   ├── components/
│   │   ├── Home/                # NEW — ReadyToPlayList, InProgressList, SessionCard,
│   │   │                        #   StoryRow, WelcomeBand, DeleteSessionDialog
│   │   └── Menu/                 # MainMenu.jsx, GameMenuItem.jsx, AdminMenuItem.jsx removed
│   │                            #   (superseded by HomePage + direct nav)
│   ├── services/gameService.js  # + deleteSession(token, sessionId)
│   └── App.jsx                   # /menu now renders HomePage
└── tests/
    ├── components/Home/…         # NEW component tests
    └── integration/home_*.test.jsx  # NEW integration tests; retire/rewrite the menu-specific ones
```

**Structure Decision**: Existing web-application layout (`src/backend`, `src/frontend`) is
kept as-is; this feature adds one backend endpoint/service method and replaces one frontend
page plus its supporting component tree, following the same module boundaries already used
by `GameSetup/` (e.g. `StoriesInProgress.jsx`) and `Admin/` component folders.

## Complexity Tracking

*No entries — no unjustified violation.*
