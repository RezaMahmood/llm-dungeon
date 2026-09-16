---
description: "Implementation plan for Remembering and Showing a Player's Avatar"
---

# Implementation Plan: Remembering and Showing a Player's Avatar

**Branch**: `034-avatar-memory-and-visibility` | **Date**: 2026-09-15 | **Spec**:
[spec.md](./spec.md)

**Input**: Feature specification from `/specs/034-avatar-memory-and-visibility/spec.md`

## Summary

Two independent additions on top of `032-story-archetypes-player-avatar`'s avatar description:
(1) the status panel gains a read-only "Who you are" section showing the session's own
`avatarDescription`, absent cleanly for a session with none; (2) a new per-`(playerId, storyId)`
Cosmos document remembers a player's most recently *used* description for that adventure, offered
back as a prefill — via the existing `GET /game/adventures/{id}` response, scoped to the caller —
and written only when a session is actually created, replacing whatever was stored before. Story
deletion cascades to delete these documents; session deletion does not touch them.

## Technical Context

**Language/Version**: Python 3.13 (backend, Azure Functions); JavaScript/JSX with React 19
(frontend) — matches the existing project, no change.

**Primary Dependencies**: Backend — `azure-cosmos` (existing) for the new
`storedAvatarDescriptions` container; no new package either side.

**Storage**: Azure Cosmos DB. One new container (`storedAvatarDescriptions`), keyed and
partitioned by `id = f"{playerId}:{storyId}"`, mirroring `avatarSetupAttempts`'s exact shape
(`032`, `avatar_setup_attempts_service.py`). No existing container's schema changes.

**Testing**: pytest (backend, mocked Cosmos service, matching every existing service test);
Vitest (frontend, existing `*.test.jsx` pattern).

**Target Platform**: Azure Functions (backend), browser SPA (frontend) — unchanged.

**Project Type**: Web application (frontend + backend), matching the existing repository layout.

**Performance Goals**: None beyond the constitution's own defaults — this slice adds one Cosmos
point-read to an existing request (`GET /game/adventures/{id}`) and one point-write to an existing
one (`POST /game/sessions`); no new call pattern.

**Constraints**: FR-011 — one player's stored description must never be reachable via another
player's request; enforced by scoping every read/write to the authenticated caller's own
`playerId`, never accepting one from the request body or query string. FR-009a — deleting a stored
description must never decrement `Story.totalTokens`.

**Scale/Scope**: One new backend model/service/container, edits to two existing services
(`play_session_service.py` for the write, `story_service.py`'s delete path composed with the new
service's cascade at the handler level — mirroring `025`'s existing composition), one existing
endpoint's response widened (`GET /game/adventures/{id}`), one existing endpoint's response
widened (`GET /game/sessions/{id}`), one status-panel component change, one setup-page prefill
wire-up. Also fixes a pre-existing bug found while tracing this data path: `gameService.js`'s
`createSession` destructures a stale `characterType` param instead of `avatarDescription`, so the
avatar text `GamePage.jsx` already collects and validates has never actually reached the backend
in the shipped `032` build — the request body's `avatarDescription` field always resolves to
`undefined`. This slice fixes that destructuring as a prerequisite: the prefill/store loop this
spec asks for cannot be tested, let alone work, while the description a player types is silently
dropped before the network call. No change to unrelated features.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — no new violation
introduced by the design below.*

- **I. Meaningful, Automated Testing**: PASS. FR-013 enumerates every behavior requiring a test;
  `quickstart.md` maps each to a concrete pytest/Vitest invocation. All backend tests mock the
  Cosmos service (existing pattern — nothing here calls a live Azure resource in tests).
- **II. Secure-by-Default Access**: PASS. No new authentication surface; the new container is
  reached only through the two already Entra ID-gated player endpoints, each scoped to the
  caller's own `playerId` (FR-011).
- **III. Defined Technology Stack**: PASS. Python/Azure Functions backend, React frontend —
  unchanged, no new language or framework.
- **IV. Right-Sized Scope — YAGNI**: PASS. One description per player per adventure, replaced not
  versioned or accumulated (Out of Scope, spec.md); no TTL, no admin view, no back-fill — each
  explicitly ruled out in the spec rather than left ambiguous.
- **V. Observability & AI Cost Transparency**: PASS/N/A. No new LLM call; FR-009a is a negative
  requirement (a delete must not decrement `Story.totalTokens`) rather than a new accrual path.
- **VI. Zero-Trust Azure Resource Communication**: PASS/N/A. The new container uses the same
  Cosmos client/Managed Identity as every existing one; no new Azure-to-Azure path.
- **VII. UI Design System & Accessibility Compliance**: PASS, verified at implementation — the
  status panel addition reuses `StatusPanel.jsx`'s existing `play-label`/`hr` pattern (no new
  visual language), and stays within the 320 px floor per FR-002/SC-001.
- **VIII. PII Protection by Design**: PASS. A stored avatar description is player-authored
  fictional character text (already established as non-PII by `032`), scoped so only its author
  can read it (FR-011) — stricter than the constitution requires, not merely compliant.
- **IX. Implementer Design Latitude**: N/A — noted, not a gate; the status panel addition is small
  enough to build directly against the existing component, no pre-implementation mockup sought.
- **X. AI Agent Division of Labor**: PASS. This plan and all downstream artifacts are local
  spec-related work; the branch will be synced with `origin/main` before implementation begins,
  per the mandatory `before_implement` hook.
- **XI. Artifacts and Code Stay Clean**: PASS. `research.md` states decisions with brief rationale
  and a short "alternatives considered" line per decision, no narrative of exploration.

No violation requires justification; **Complexity Tracking is not needed.**

## Project Structure

### Documentation (this feature)

```text
specs/034-avatar-memory-and-visibility/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

No `contracts/` directory: both surfaces this slice touches are existing internal request/response
shapes gaining one field each (`GET /game/adventures/{id}` response gains `avatarDescription`;
`GET /game/sessions/{id}` response gains `avatarDescription`) rather than a new externally-facing
interface — matching `032`'s and `033`'s precedent of skipping `contracts/` for an internal-only
change. Exact field-level shape is `tasks.md`'s concern.

### Source Code (repository root)

```text
src/backend/
├── models/
│   └── stored_avatar_description.py       # NEW — id, playerId, storyId, description, entityType
├── services/
│   ├── stored_avatar_description_service.py   # NEW — get/store/delete_for_story
│   ├── play_session_service.py                # create_session: store on success (FR-005, FR-012)
│   └── story_service.py                       # unchanged; cascade composed at handler level
├── api/
│   ├── admin/stories.py                # delete_story handler: cascade the new service (FR-009)
│   └── game/
│       ├── adventures.py               # get_adventure: include caller's stored description
│       └── sessions.py                 # get_session: include session's avatarDescription
├── config.py                           # STORED_AVATAR_DESCRIPTIONS_CONTAINER constant
└── tests/unit/
    ├── test_stored_avatar_description_service.py   # NEW
    ├── test_play_session_service.py
    ├── test_admin_stories.py (or equivalent delete-cascade test)
    ├── test_game_adventures.py
    └── test_game_sessions.py

src/frontend/
├── src/
│   ├── components/Play/StatusPanel.jsx     # avatarDescription prop, read-only section
│   ├── pages/PlayPage.jsx                  # thread avatarDescription through to StatusPanel
│   ├── pages/GamePage.jsx                  # prefill from getAdventure; pass through to PlayPage
│   └── services/gameService.js             # fix createSession's stale `characterType` param
└── tests/
    ├── components/Play/StatusPanel.test.jsx
    └── integration/game_setup_flow.test.jsx / play_status_panel tests (existing files extended)

infrastructure/terraform/main.tf   # new azurerm_cosmosdb_sql_container + env var wiring
```

**Structure Decision**: Existing web-application layout (`src/backend`, `src/frontend`),
unchanged. This slice touches both sides plus the Terraform container definition; no new
top-level directory.

## Complexity Tracking

No violations — this section is not needed.
