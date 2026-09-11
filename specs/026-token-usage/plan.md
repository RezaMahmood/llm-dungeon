# Implementation Plan: Story and Session Token Usage Tracking

**Branch**: `026-token-usage` | **Date**: 2026-09-11 | **Spec**: `specs/026-token-usage/spec.md`

**Input**: Feature specification from `/specs/026-token-usage/spec.md`

## Summary

Persist the LLM token usage this project's telemetry already computes onto
the records it was spent on. A `Story` gains a cumulative `totalTokens`
field covering its authoring lifecycle (creation, edits/regenerations,
admin test plays), shown as a new column in the admin stories list; the
existing always-visible last-published date moves behind a hover on the
Published status indicator to make room for it. Separately, every gameplay
turn (real player or admin test play) is tokened and rolled into a running
per-session total, surfaced on a new, read-only admin "Sessions" page
listing every session's story, session id, token total, and the email of
whoever played it — reachable as its own admin navigation item. Player
session tokens never roll into the story's total (clarified with the
user); test-play tokens roll into both the story's total and the test
session's own total, since they answer two different questions. No new
container, dependency, or technology is introduced; four existing entities
each gain one or two fields (research.md, data-model.md).

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 19 via Vite (frontend, existing)

**Primary Dependencies**: No new dependencies — reuses the existing `azure-cosmos` `CosmosService`/container-client pattern (`StoryService`, `StoryDraftService`, `PlaySessionService`, `TestPlaySessionService`, `AccountProvisioningService`) and the existing `authorize_admin`/`authorize_player` middleware.

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — the existing `stories`, `storyDrafts`, `playSessions`, and `testPlaySessions` containers each gain one or two new fields (data-model.md); no new container.

**Testing**: pytest (backend `src/backend/tests/unit`, `src/backend/tests/integration`, existing convention); Vitest + React Testing Library (frontend `src/frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `src/backend/` + `src/frontend/` structure)

**Performance Goals**: N/A — this is a low-frequency, deliberate administrator-viewed report and a per-record counter update piggybacked on calls the system already makes; no new throughput/latency target is stated (Principle IV). The new `GET /api/manage/sessions` endpoint's cost scales with total session count across two containers, acceptable at this project's stated scale (spec.md Assumptions: no pagination/filtering for v1).

**Constraints**: No historical backfill for stories/sessions persisted before this feature ships — they start at `0` (spec.md Assumptions). No pagination, filtering, or sorting on the Sessions page in v1. Token totals are persisted counters, never computed live from telemetry at read time (research.md Decision 1). Email and story name on the Sessions page are resolved live, never snapshotted onto a session document (research.md Decision 7).

**Scale/Scope**: Same small administrator/player population as prior features. Backend: one changed method signature chain through `LLMService` and its four callers, two extended entities' read-modify-write paths (`StoryService`, `StoryDraftService`, `PlaySessionService`, `TestPlaySessionService`), one new small service (session overview), one new endpoint, one changed endpoint response. Frontend: one new column + one hover affordance in the existing stories list, one new page, one new nav item, one new service module. One constitution amendment (research.md Decision 9).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — Edge Cases in spec.md enumerate the cases needing tests: pre-existing story/session at zero, a failed/content-filtered turn contributing zero tokens, concurrent writes not clobbering each other's totals, a deleted story's session still rendering, an unprovisioned player/tester's session still rendering, story-total exclusion of real player turns. contracts/api.md and quickstart.md give concrete shapes for each.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — The new `GET /api/manage/sessions` endpoint is gated by the existing `authorize_admin` middleware, the same gate every other `/api/manage/*` endpoint already uses; no anonymous access, no new permission tier.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — No pagination/filtering/sorting is built for the Sessions page (spec.md Assumptions); email/story-name resolution reuses existing lookup shapes rather than introducing a new cross-reference table (research.md Decision 7); a lost `ensure_starting_point` etag race is accepted as a negligible undercount rather than engineered away (research.md Decision 2).

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET / Enhanced — This feature persists, per-record, exactly the token counts the existing OpenTelemetry spans in `llm_service.py` already compute (Principle VI, Observability & Telemetry Requirements); it changes no telemetry emission, only adds a second, persisted consumer of the same numbers. The aggregate Application Insights view (024-azure-monitoring-dashboard) is unaffected and remains the source for spend trends over time; this feature answers a different question ("what did *this* story/session cost") that a per-record telemetry query cannot answer quickly enough for a list view (research.md Decision 1).

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — Reuses `CosmosService`'s existing Managed Identity authentication; no new credential, connection type, or Azure resource.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET — The new Tokens column and Sessions page reuse the existing `.table`/`tag`/`text-muted` classes, no new visual component. The hover affordance uses the native HTML `title` attribute rather than a new tooltip primitive, since the design system defines none today (research.md Decision 8) — this introduces nothing for the principle to arbitrate, as a native attribute carries no visual design of its own. Status is still conveyed as text, not color alone (existing tag pattern, unchanged).

### Principle IX – Playtesting-Driven Quality (Post-Ship Verification, Non-Blocking)
**Status**: ✓ MET — Complete once automated tests pass and CI's gate is green; no pre-implementation human sign-off required.

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: ✓ MET, with care — The Sessions page surfaces a player's/tester's email, which is PII. Per PII & Data Protection Requirements, this is permitted because this spec explicitly requires it (FR-015) and the surface is access-controlled (Principle II, admin-only). Email is resolved live from the existing `ProvisionedAccountEntry` store — never duplicated onto a session document — keeping PII in exactly one store rather than two (research.md Decision 7). Per-turn token counts are stripped from the player-facing session-detail response (research.md Decision 6) — not because they are PII, but to avoid leaking internal cost data into a player-facing payload unnecessarily.

### Principle XI – Implementer Design Latitude (Non-Blocking)
**Status**: ✓ MET — No pre-implementation mockup is required; the Sessions page's exact layout and copy are left to the implementer within Principle VIII's constraints and the screen contract added per Decision 9 below.

### Principle XII – Right-Sized Scope — Not Enterprise-Grade (NON-NEGOTIABLE)
**Status**: ✓ MET — No new environment, identity federation, role hierarchy, or scaling infrastructure. No pagination/filtering is added preemptively (spec.md Assumptions). The Sessions page is available to any existing Administrator — no narrower permission tier is introduced (spec.md Assumptions).

### Principle XIII – AI Agent Division of Labor (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A at planning time — Governs the GitHub-hosted handoff (PR creation, labelling, review, merge) rather than technical design; will be followed when this feature's implementation is pushed.

### Security & Access Control Requirements (constitution, non-principle section)
**Status**: ✓ MET — No secrets introduced; the new endpoint is only reachable by an authenticated, allow-listed Administrator.

### Screen contracts (constitution, UI Design System Requirements)
**Status**: ⚠ ACTION REQUIRED, not yet MET — The stories-list Tokens column and hover extend the existing "Administrator — stories & configuration" contract (no amendment needed for that part). The new **Sessions** page has no existing screen contract, and the constitution requires one before a feature may ship a new screen. This feature's implementation MUST include a constitution amendment adding an "Administrator — sessions" entry to the Screen contracts list — no prototype, deferring visual design to the implementer within Principle VIII's constraints — following the precedent `012-story-editing-and-review` set when it added the "Administrator — stories & configuration" entry the same way (research.md Decision 9). This amendment is a governance step to perform during implementation (via `/speckit-tasks`' generated task list and a constitution PR), not a violation being justified away here.

No unjustified violations — Complexity Tracking table is not needed; the one open item above is a planned governance action, not a rejected simpler alternative.

## Project Structure

### Documentation (this feature)

```text
specs/026-token-usage/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout (`src/backend/` Python Azure Functions + `src/frontend/` React SPA). This feature extends the existing `Story`/`StoryDraft`/`PlaySession`/`TestPlaySession` models and services, the existing admin stories list, and adds one new frontend page + one new small backend service; it introduces no new container.

```text
src/backend/
├── models/
│   ├── story.py                                 # MODIFY: Story gains totalTokens: int = 0
│   ├── story_draft.py                           # MODIFY: StoryDraft gains totalTokens: int = 0
│   ├── play_session.py                          # MODIFY: PlaySession gains totalTokens: int = 0;
│   │                                             #   PlayerInteraction gains tokens: int = 0
│   └── test_play_session.py                     # MODIFY: TestPlaySession gains totalTokens: int = 0;
│                                                 #   TestPlayExchange gains tokens: int = 0
├── services/
│   ├── llm_service.py                           # MODIFY: _call() and every public generation method
│   │                                             #   (suggest_world_prompt, generate_story_config,
│   │                                             #   generate_starting_point, generate_gameplay_turn,
│   │                                             #   summarize_session_history) return (payload,
│   │                                             #   tokens_used) (research.md Decision 1)
│   ├── story_draft_service.py                   # MODIFY: accumulate StoryDraft.totalTokens on
│   │                                             #   suggest_world_prompt; fold draft + generation
│   │                                             #   tokens into the new Story on generate_story;
│   │                                             #   fold draft + regeneration tokens into the
│   │                                             #   existing Story on save_draft_to_story
│   ├── story_service.py                         # MODIFY: derived_content/_generate_narrative_guidance/
│   │                                             #   _generate_starting_point/ensure_starting_point/
│   │                                             #   import_configuration accumulate totalTokens;
│   │                                             #   record_test_play(story_id, tokens_used) also
│   │                                             #   increments Story.totalTokens; list_summaries
│   │                                             #   projects totalTokens
│   ├── play_session_service.py                  # MODIFY: _generate_and_persist_turn sets each
│   │                                             #   turn's tokens and adds to session.totalTokens;
│   │                                             #   _summarize_if_due adds summary tokens to
│   │                                             #   session.totalTokens; get_session_detail_for_player
│   │                                             #   strips tokens from each returned turn
│   ├── test_play_session_service.py             # MODIFY: _generate_and_persist_turn sets each
│   │                                             #   exchange's tokens, adds to session.totalTokens,
│   │                                             #   and passes tokens_used to record_test_play
│   └── session_overview_service.py              # NEW: SessionOverviewService.list_sessions() —
│                                                 #   projects both session containers, resolves story
│                                                 #   name (fallback "(deleted story)") and email via
│                                                 #   AccountProvisioningService.list_all() (fallback
│                                                 #   "(no longer provisioned)") (research.md Decision 7)
├── services/story_config_file.py                # MODIFY: add "totalTokens" to SYSTEM_MANAGED_KEYS
├── api/
│   └── admin/
│       ├── stories.py                           # MODIFY: list_stories response already passes through
│       │                                         #   list_summaries' new totalTokens field
│       └── sessions.py                          # NEW: list_sessions handler (authorize_admin ->
│                                                 #   SessionOverviewService.list_sessions())
├── function_app.py                              # MODIFY: register GET manage/sessions
└── tests/
    ├── unit/
    │   ├── test_llm_service.py                  # MODIFY: every public method's (payload, tokens)
    │   │                                         #   return shape
    │   ├── test_story_draft_service.py          # MODIFY: draft.totalTokens accumulation; folding
    │   │                                         #   into Story on generate/save
    │   ├── test_story_service.py                # MODIFY: totalTokens accumulation paths;
    │   │                                         #   record_test_play's dual increment;
    │   │                                         #   list_summaries projection
    │   ├── test_play_session_service.py         # MODIFY: per-turn tokens, session total,
    │   │                                         #   summarization tokens, player-facing stripping,
    │   │                                         #   no contribution to Story.totalTokens
    │   ├── test_test_play_session_service.py    # MODIFY: per-exchange tokens, session total,
    │   │                                         #   dual contribution to Story.totalTokens
    │   └── test_session_overview_service.py     # NEW: combined listing, deleted-story fallback,
    │                                             #   unprovisioned-account fallback, zero-turn session
    └── integration/
        ├── test_admin_stories_endpoint.py       # MODIFY: totalTokens in list/get responses
        └── test_admin_sessions_endpoint.py      # NEW: full GET /api/manage/sessions lifecycle,
                                                  #   401/403 without admin auth, empty list

src/frontend/
├── src/
│   ├── pages/
│   │   ├── AdminPage.jsx                        # MODIFY: add Tokens column; add title attribute
│   │   │                                         #   (last-published date) to the Status tag; pass a
│   │   │                                         #   new prop to StoryPublishActions suppressing its
│   │   │                                         #   own inline last-published text in this context
│   │   └── AdminSessionsPage.jsx                # NEW: read-only table — Story, Session ID,
│   │                                             #   Total Tokens, Email
│   ├── components/
│   │   ├── Admin/
│   │   │   └── StoryPublishActions.jsx          # MODIFY: new prop (e.g. hideStatusLine) suppresses
│   │   │                                         #   the inline "Status: ... last published" text;
│   │   │                                         #   unchanged everywhere it isn't passed
│   │   └── Layout/
│   │       └── NavBar.jsx                       # MODIFY: add "Sessions" link in the admin nav
│   │                                             #   variant, alongside Stories/New story/People
│   └── services/
│       └── sessionService.js                    # NEW: listSessions(token) -> GET /manage/sessions
├── App.jsx                                      # MODIFY: register /admin/sessions route
│                                                 #   (ProtectedRoute capability="Administrator")
└── tests/
    ├── pages/
    │   ├── AdminPage.test.jsx                   # MODIFY: Tokens column rendering, zero-token
    │   │                                         #   fallback, hover date, absence of inline date text
    │   └── AdminSessionsPage.test.jsx           # NEW: row rendering for player and test sessions,
    │                                             #   deleted-story and unprovisioned-account fallbacks,
    │                                             #   read-only (no action controls)
    └── components/
        └── StoryPublishActions.test.jsx         # MODIFY: hideStatusLine suppresses inline text;
                                                  #   default (unset) behavior unchanged
```

## Constitution amendment (companion to this feature)

Per the Screen contracts item above, implementation of this feature MUST be
accompanied by a small amendment to `.specify/memory/constitution.md`
adding, under Screen contracts:

> **Administrator — sessions** (no prototype screen) — a read-only list of
> every gameplay session (real player and admin test play), each row
> showing its story, a session identifier, its cumulative token total, and
> the email of whoever played it. Reachable as its own admin navigation
> item alongside Stories and People. Introduced by `026-token-usage`,
> whose spec defers this screen's visual design; that deferral is recorded
> as an explicit exception in this plan and covers styling only.

This is a MINOR version bump (a new section/contract entry, per the
constitution's own versioning rule) and follows the same amendment PR
process every other constitution change does (Governance section).
