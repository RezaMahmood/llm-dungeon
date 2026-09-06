# Implementation Plan: Core Gameplay

**Branch**: `008-core-gameplay` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-core-gameplay/spec.md`

## Summary

Once a player has completed setup (`006-adventure-and-character-setup`), this feature
implements the actual play loop: creating a server-persisted Play Session, generating a
narrative response to each free-text player action via the LLM, retaining session
history/state across requests (periodically summarized every 20 turns to bound context),
screening input/output for unsafe content, deflecting attempts to override the system's
behavior or reveal its instructions, rate-limiting submissions, enforcing single-owner
session exclusivity, ensuring at most one of a player's own sessions is active at a time
(with an explicit resume step to switch back), escalating repeated content-safety
violations to a cross-session 1-hour lockout, and automatically ending the session once
its adventure's configured completion criteria (duration, success, and/or failure,
combined via an any/all rule) are satisfied.

Technical approach: a new `PlaySession` entity persisted in a new `playSessions` Cosmos
container (one document per playthrough), a new `POST /api/game/sessions` endpoint that
creates a session and generates its opening narrative (superseding
`POST /api/game/start`'s role), a new `POST /api/game/sessions/{sessionId}/interactions`
endpoint that generates each subsequent turn, and a new
`POST /api/game/sessions/{sessionId}/resume` endpoint that reactivates a session the
player previously left for another (FR-015). Both interaction-bearing endpoints reuse the
existing `authorize_player` middleware and `LLMService`'s structured-output call pattern,
extended with a per-turn schema that also reports which of the story's completion
conditions the turn newly satisfies. Session exclusivity (between players) and rate
limiting are enforced via the session document's own state (ETag optimistic concurrency,
`lastInteractionAt`) — no new infrastructure. A player's own cross-session exclusivity
(FR-015) is enforced via an `isActiveForPlayer` flag on each of that player's `PlaySession`
documents: creating or resuming a session sets its flag and clears any other of that
player's sessions found active via a cross-partition query on `playerId`, and
`submit_interaction` rejects with 409 when the target session's flag is false. Content-
safety screening relies on the already-provisioned Foundry deployment's default content
filter, mapped to a safe in-fiction narrative rather than a raw error; a hardened system
prompt keeps every turn in-fiction and immune to override attempts without a second LLM
call. A small second Cosmos container (`playerContentSafetyStandings`) tracks each
player's flagged-submission count and any resulting 1-hour lockout across sessions. Every
20 turns, an additional `LLMService` call condenses prior history into a `summary` field
stored on the same `PlaySession` document, used as context from the next turn onward. See
[research.md](./research.md) for the technical decisions behind this approach.

## Technical Context

**Language/Version**: Python 3.11 (backend, Azure Functions), JavaScript/JSX + React 18 (frontend)

**Primary Dependencies**: `azure-functions`, existing `CosmosService`/`LLMService`/
`StoryService`/`AccountProvisioningService` (backend, all reused unchanged in kind);
React Router, existing design-token layer (`specs/designs/styles.css`) (frontend)

**Storage**: Azure Cosmos DB — new `playSessions` container (partition key `/id`) and new
`playerContentSafetyStandings` container (partition key `/id`); reads the existing
`stories` container, no schema change there

**Testing**: `pytest` (backend unit + integration, mirroring existing `tests/unit` /
`tests/integration` structure and the in-memory OTel exporter fixtures in `conftest.py`),
existing frontend component test setup (Vitest/RTL)

**Target Platform**: Azure Functions (backend), browser SPA served as a static web app (frontend)

**Performance Goals**: SC-001 — a narrative response within a few seconds of a submitted
action; met by a single LLM call per turn (research.md Decision 6), matching the existing
`llm_service.py` call pattern's observed latency.

**Constraints**: Server-side validation and enforcement for every gameplay rule (session
exclusivity, rate limiting, completion criteria, content safety) per Constitution
Principle II — none of this is client-trusted; every LLM call is fully traced (prompt,
response, tokens, cost, latency) per Principle VI, same as `llm_service.py`'s existing
calls.

**Scale/Scope**: Two new backend endpoints, two new Cosmos containers/models (one
service), two `LLMService` methods (one extended/new gameplay-turn method with a richer
structured-output schema, one new summarization method), one rebuilt frontend play page.
No new external dependency, no new Azure resource type.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing**: Each FR (001-014) and each Edge Case gets a
  dedicated automated test — session creation/opening narrative, per-turn narrative
  generation and history retention, concluded-session rejection, exclusivity/concurrency
  rejection, rate-limit rejection, content-safety deflection, anti-override deflection,
  3-strike lockout, 20-turn summarization, and each duration/success/failure/any/all
  completion combination (quickstart.md Scenarios 1-8). PASS.
- **II. Secure-by-Default Access**: All three endpoints require Entra ID auth + `Player`
  role via the existing `authorize_player` middleware, unchanged. Session ownership
  (`playerId == authenticated user`) is checked server-side on every interaction and on
  resume — a non-owner gets a generic 403, never session existence/content. All setup
  fields are re-validated server-side at session creation, not trusted from an earlier
  request. Active/inactive session state (FR-015) is likewise enforced server-side only —
  never left to the client to self-report which session it considers "current". PASS.
- **III. Defined Technology Stack**: Python/Azure Functions backend, ReactJS frontend — no
  deviation. PASS.
- **IV. Simplicity Over Premature Scale**: Exclusivity and rate limiting are enforced via
  the session document's own ETag/timestamp fields rather than a new locking or
  rate-limiting service; content-safety screening reuses the already-provisioned model
  deployment's default filter rather than a second Content Safety resource; the
  anti-override guardrail is a prompt instruction on the existing per-turn call rather
  than a second classifier call; session summarization is a sibling field on the same
  `PlaySession` document rather than a new document type; the 3-strike lockout uses one
  small new container with the same point-read/conditional-write pattern already used for
  `playSessions`, not a new service (research.md Decisions 2-4, 8-10). PASS.
- **V. Continuous Integration Gate**: New/changed tests run in the existing CI pipeline; no
  CI config change needed. PASS.
- **VI. Observability & AI Cost Transparency**: Every LLM call this feature makes (opening
  narrative, each turn) goes through `LLMService`'s existing traced `_call` wrapper —
  prompt, response, token counts, cost, and latency captured identically to
  `004-story-creation-done`'s calls, attributable to a `sessionId`/player action. PASS.
- **VII. Zero-Trust Azure Resource Communication**: No new Azure resource dependency; the
  new `playSessions` and `playerContentSafetyStandings` containers both use the same
  Managed-Identity-authenticated `CosmosService` and account-level role assignment
  already in place — no new role assignment needed. PASS.
- **VIII. UI Design System & Accessibility Compliance**: The play surface is built exactly
  to the `specs/designs/03-play.html` screen contract (scrolling story pane; fixed title
  bar, input row, suggested actions, and status panel; status panel shows location/goal/
  progress) using only the vendored design-token layer and shared component classes — no
  ad hoc styling. The "Stuck? Get a hint" action visible in that mockup is explicitly out
  of scope for this feature's functional requirements (spec.md Design Reference note) and
  is rendered inert/omitted rather than wired to nonexistent behavior. Free-text input
  remains available at all times alongside suggested actions (Constitution "Readability &
  interaction requirements" #4-5). The title bar's exit action routes through a
  `PauseDialog` confirmation stating where the game was saved (FR-016, Constitution "Save
  and session behaviour" #3) — exiting never happens unconfirmed. The title bar also
  carries a static "Autosaved after every turn" label (FR-017, Constitution "Save and
  session behaviour" #1), disclosing the autosave-per-interaction behavior `submit_
  interaction` already performs by construction. PASS.
- **IX. Playtesting-Driven Quality**: Non-blocking per the current constitution — automated
  tests (above) are the completion gate; a playtesting task may be included in `tasks.md`
  as informational only. PASS.
- **X. PII Protection by Design**: `PlaySession` stores only `playerId` (an opaque Entra
  `oid`, already used this way elsewhere in the codebase, e.g. `Story.createdBy`),
  player-chosen fictional `characterName`, and narrative text — no real name, email, or
  other PII. `PlayerContentSafetyStanding` likewise keys only on that same opaque `oid`
  and stores a count/timestamp, no content or PII. LLM prompt/response telemetry
  (Principle VI) carries the same non-PII content. PASS.
- **XI. Implementer Design Latitude**: No pre-implementation mockup sign-off required; the
  existing `03-play.html` mockup is itself the acceptance reference (Principle VIII,
  above), so there is no undesigned surface this feature introduces. PASS.
- **XII. Right-Sized Scope**: No new environment, identity pattern, or scaling
  infrastructure introduced — session exclusivity, rate limiting, and content safety are
  all built from primitives already in this project (research.md Decisions 2-4). PASS.
- **XIII. AI Agent Division of Labor**: Standard — local work, then `gh pr create` labelled
  `AI Generated`/`Claude`, no auto-merge. PASS (process, not a design concern).

**Result**: No unjustified violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-core-gameplay/
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
│   └── game/
│       ├── sessions.py             # NEW — POST /api/game/sessions, POST .../interactions,
│       │                            #       POST .../resume (FR-015)
│       ├── middleware.py           # existing authorize_player — reused unchanged
│       ├── start.py                # RETIRED — superseded by sessions.py (contracts/api.md)
│       └── adventures.py           # existing — unchanged
├── models/
│   ├── play_session.py             # NEW — PlaySession, PlayerInteraction (data-model.md)
│   └── player_content_safety_standing.py  # NEW — PlayerContentSafetyStanding (data-model.md)
├── services/
│   ├── play_session_service.py     # NEW — session lifecycle, exclusivity (cross-player +
│   │                                #       FR-015 own-session), completion-rule evaluation
│   │                                #       (added in Phase 4, tasks.md), lockout
│   │                                #       enforcement, summarization trigger
│   ├── llm_service.py              # EXTENDED — new structured-output method for gameplay turns
│   │                                #       (with anti-override guardrail) + summarization method
│   ├── prompts/
│   │   ├── gameplay_turn_system_prompt.txt     # NEW — mirrors existing exchange/generation prompt files
│   │   └── gameplay_summary_system_prompt.txt  # NEW — condenses prior turns into `summary` (FR-014)
│   └── story_service.py            # existing — unchanged (read-only reuse)
└── tests/
    ├── unit/
    │   ├── test_play_session_service.py   # NEW — includes lockout + summarization-trigger tests
    │   └── test_llm_service.py            # EXTENDED — new gameplay-turn + summarization methods
    └── integration/
        └── test_game_sessions_endpoint.py # NEW — includes 423 lockout, anti-override cases

src/frontend/
├── src/
│   ├── pages/
│   │   └── PlayPage.jsx            # NEW (or GamePage.jsx extended) — the 03-play.html surface
│   ├── components/
│   │   └── Play/                   # NEW — StoryPane, StatusPanel, InstructionInput, SuggestedActions, PauseDialog
│   └── services/
│       └── gameService.js          # EXTENDED — createSession/submitInteraction calls
└── tests/
    └── Play/                       # NEW — component tests per piece + concluded-session gating

infrastructure/terraform/
└── main.tf                         # EXTENDED — new azurerm_cosmosdb_sql_container resources
                                     #   "play_sessions" and "player_content_safety_standings"
```

**Structure Decision**: Existing web-application split (`src/backend`, `src/frontend`) is
reused as-is. New files land inside the existing `api/game`, `models`, `services`, and
`pages`/`components` trees, following the same file-per-concern pattern as
`004-story-creation-done` and `006-adventure-and-character-setup`. `start.py` is retired
rather than kept alongside `sessions.py`, since `006`'s plan already scoped it as a
placeholder pending this feature's session-creation logic (contracts/api.md).

## Complexity Tracking

*No Constitution Check violations requiring justification — table intentionally omitted.*
