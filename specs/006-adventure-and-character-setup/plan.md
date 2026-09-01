# Implementation Plan: Adventure and Character Setup

**Branch**: `006-adventure-and-character-setup` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-adventure-and-character-setup/spec.md`

## Summary

A player who chooses "start a new game" must, in order: (1) pick a published adventure from
a list, (2) enter a character name, and (3) pick one of that adventure's administrator-defined
character types — before actual gameplay can begin. This feature adds the player-facing setup
flow only; the play session itself is out of scope (`008-core-gameplay`).

Technical approach: add a new player-scoped, published-only summary endpoint
(`GET /api/game/adventures`) and extend the existing `POST /api/game/start` placeholder to
validate the three setup inputs server-side (adventure exists+published, name non-blank
≤50 chars, character type valid for that adventure) and return a `setup complete` confirmation
— it still does not create a play session (that's `008-core-gameplay`). Both endpoints share a
new `authorize_player` middleware, mirroring the existing `authorize_admin` pattern. The
3-step flow (adventure → name → character type) is built inside the existing `/game` route
(`GamePage.jsx`), replacing its placeholder content — no new route. No new persisted entity:
this reuses the existing `Story`/`CharacterType` models and Cosmos container from
`004-story-creation`.

## Technical Context

**Language/Version**: Python 3.11 (backend, Azure Functions), JavaScript/JSX + React 18 (frontend)

**Primary Dependencies**: `azure-functions`, existing `CosmosService`/`AccountProvisioningService` (backend); React Router, existing design-token layer (`specs/designs/styles.css`) (frontend)

**Storage**: Azure Cosmos DB — existing `Stories` container (no schema change; reads only)

**Testing**: `pytest` (backend unit + integration), existing frontend component test setup (Vitest/RTL, matching prior features)

**Target Platform**: Azure Functions (backend), browser SPA served as a static web app (frontend)

**Project Type**: Web application (frontend + backend, per repo's existing `src/frontend` / `src/backend` split)

**Performance Goals**: N/A — no stated throughput/latency requirement beyond existing endpoint norms (Constitution Principle IV: no scale not yet required)

**Constraints**: Server-side validation is mandatory for all three setup inputs (Constitution Principle II — client-side checks alone are insufficient); every endpoint requires Entra ID auth + Player role allow-listing (Principle II)

**Scale/Scope**: One new backend endpoint, one extended existing endpoint, one new middleware function, one existing frontend page rebuilt as a 3-step flow. No new persisted entity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing**: Each of FR-001 through FR-007 gets a corresponding
  automated test (backend: adventure listing, name/type/adventure validation, completeness
  gate; frontend: step gating, error messaging, reset-on-adventure-change). PASS.
- **II. Secure-by-Default Access**: Both `GET /api/game/adventures` and `POST /api/game/start`
  require Entra ID auth + explicit `Player` role via a new `authorize_player` middleware
  (mirrors `authorize_admin`); all setup validation (adventure published, name length, type
  membership) is enforced server-side, not just client-side. PASS.
- **III. Defined Technology Stack**: Python/Azure Functions backend, ReactJS frontend — no
  deviation. PASS.
- **IV. Simplicity Over Premature Scale**: Reuses existing Cosmos container and Story model;
  no new entity, no new infrastructure. PASS.
- **V. Continuous Integration Gate**: New/changed tests run in the existing CI pipeline; no
  change to CI config needed. PASS.
- **VI. Observability & AI Cost Transparency**: N/A — this feature makes no LLM calls itself.
  No new telemetry requirement beyond existing endpoint-level tracing already in place. PASS.
- **VII. Zero-Trust Azure Resource Communication**: No new Azure resource dependency; reuses
  existing Cosmos access via `CosmosService` (already Managed Identity-based). PASS.
- **VIII. UI Design System & Accessibility Compliance**: The adventure-list step reuses the
  card-list pattern already specified in `specs/designs/02-story-select.html` ("Start something
  new" section — kicker = tone·sessionLengthMinutes, title = name, meta = "Reading level: X").
  The name-entry and character-type steps are **new UI not covered by any existing design
  mockup** — see Constitution Principle XI below; they MUST be built from the same design-token
  layer and shared component classes (form field, segmented control/radio-card pattern) as
  every other screen, with no ad hoc styling. PASS, pending Principle XI sign-off.
- **IX. User-Verified Acceptance Before Completion**: `tasks.md` will end with an explicit
  user-verification task against the deployed (or most representative available) environment.
  PASS (planned).
- **X. PII Protection by Design**: Character names are player-chosen fictional labels, not PII,
  and are stored only in the eventual play-session record (owned by `008-core-gameplay`), not
  logged. No PII is introduced by this feature. PASS.
- **XI. UI Design Pre-Agreement Before Implementation (NON-NEGOTIABLE)**: **GAP, not yet
  satisfied.** `specs/designs/02-story-select.html` covers only the adventure-selection card
  list; there is no existing mockup for the character-name-entry or character-type-selection
  steps. Per this principle, `tasks.md` MUST include an explicit design-agreement/sign-off task
  — covering the two new steps' layout — sequenced before any implementation task, and that
  task is not complete until the requesting user/product owner confirms the design. This plan
  does not itself resolve the gap; Phase 1 design docs will describe the two new steps'
  *content contract* (what fields/choices they present) without prescribing pixel layout, and
  the sign-off task in `tasks.md` is where the actual mockup gets agreed.

**Result**: No unjustified violations. One explicit, tracked gate (Principle XI) carried
forward into `tasks.md` as required, rather than resolved here.

## Project Structure

### Documentation (this feature)

```text
specs/006-adventure-and-character-setup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api.md           # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/backend/
├── api/
│   ├── admin/
│   │   └── middleware.py          # existing authorize_admin — pattern to mirror
│   └── game/
│       ├── start.py                # existing placeholder — extended with setup validation
│       ├── adventures.py           # NEW — GET /api/game/adventures (list) and
│       │                           #   GET /api/game/adventures/{adventureId} (detail) handlers
│       └── middleware.py           # NEW — authorize_player (mirrors admin/middleware.py)
├── models/
│   └── story.py                    # existing Story/CharacterType — reused, unchanged
├── services/
│   └── story_service.py            # existing — reused; may gain a published-only summary query
└── tests/
    ├── unit/
    │   ├── test_game_middleware.py         # NEW
    │   └── test_game_start_validation.py   # NEW
    └── integration/
        ├── test_game_adventures_endpoint.py  # NEW
        └── test_game_start_endpoint.py       # extended

src/frontend/
├── src/
│   ├── pages/
│   │   └── GamePage.jsx            # rebuilt: 3-step setup flow (adventure → name → type)
│   ├── components/
│   │   └── GameSetup/              # NEW — AdventureList, CharacterNameStep, CharacterTypeStep
│   └── services/
│       └── gameService.js          # NEW or extended — calls the two endpoints above
└── tests/
    └── GameSetup/                  # NEW — component tests per step + completeness gate
```

**Structure Decision**: Existing web-application split (`src/backend`, `src/frontend`) is
reused as-is. No new top-level directories; new files land inside the existing `api/game`,
`services`, and `pages`/`components` trees, following the same file-per-concern pattern as
`004-story-creation` and `005-story-publishing`.

## Complexity Tracking

*No Constitution Check violations requiring justification — table intentionally omitted.*
