# Implementation Plan: Story Delete

**Branch**: `025-story-delete` | **Date**: 2026-09-07 | **Spec**: `specs/025-story-delete/spec.md`

**Input**: Feature specification from `/specs/025-story-delete/spec.md`

## Summary

Add a permanent delete action for a `Story`, reachable only from the administrator story list's per-row control, distinct from — and stronger-confirmed than — the existing publish/unpublish action (`005-story-publishing-done`). Deleting removes the `Story` document from the `stories` container outright and permanently deletes every currently-active `PlaySession` (`008-core-gameplay-done`) referencing it, regardless of which player owns it. This feature also amends unpublish's own behavior: an unpublished story's in-progress sessions are never deleted, but become non-continuable, computed live from the story's current `published` state rather than stored on the session. Both cases are discovered lazily — only when a player next submits a turn, resumes, reads session detail, or loads their in-progress-games list — never via a background job or push notification. A player is always told the specific reason ("Story has been deleted" vs. "Story has been unpublished"), and their in-progress-games list shows a deleted story's game as absent and an unpublished story's game as greyed out (automatically restored on re-publish). No new entity, container, or technology is introduced.

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 19 via Vite (frontend, existing)

**Primary Dependencies**: No new dependencies — reuses the existing `azure-cosmos` `CosmosService`/container-client pattern (`StoryService`, `PlaySessionService`) and the existing `authorize_admin`/`authorize_player` middleware.

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — the existing `stories` and `playSessions` containers; this feature adds no new fields or containers. Delete uses `delete_item` against each; unpublish's effect is computed live by reading `Story.published` at the moments it matters (see data-model.md).

**Testing**: pytest (backend `src/backend/tests/unit`, `src/backend/tests/integration`, existing convention); Vitest + React Testing Library (frontend `src/frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `src/backend/` + `src/frontend/` structure)

**Performance Goals**: N/A — delete is a single low-frequency, deliberate administrator action with no stated throughput/latency target (Principle IV). The cascade's cost scales with the number of players currently mid-game on the one deleted story, which is small at this project's scale. The live-availability check adds one existing-shape point read per turn/resume/detail request, not a new one.

**Constraints**: No undo/trash/recovery mechanism for a deleted story or its removed sessions (Assumptions — an administrator who wants recoverability should unpublish instead, which the confirmation dialog reminds them of); no bulk/multi-select delete (Assumptions, mirroring `005`'s FR-014); the delete confirmation is a client-side safeguard only, never a server-side precondition (mirroring `005`'s FR-013 pattern for unpublish); no new background job, scheduled task, or real-time/push channel is introduced anywhere in this feature.

**Scale/Scope**: Same small administrator/player population as prior features; one new backend endpoint, changed error-mapping and one new availability check across three existing session endpoints, one changed list-response shape, one new frontend action component + hook mirroring the existing publish/unpublish pair, two new notice branches on the play surface, and a greyed-out row state in the in-progress-games list.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-014 enumerates every distinct outcome needing a test (delete with/without active sessions, unpublish leaving sessions intact but non-continuable, cancelled confirmation, delete-of-already-deleted as 404, the "deleted" and "unpublished" next-turn messages, list row absent vs. greyed out, restore on re-publish); contracts/api.md and quickstart.md give concrete request/response shapes for each.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — The new `DELETE /api/manage/stories/{storyId}` endpoint is gated by the existing `authorize_admin` middleware; no anonymous access. The changed session endpoints still run behind the existing `authorize_player` check — only the response body/shape for an already-authorized session or list changes.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model; extends the existing Python/Azure Functions + React stack.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — Reuses existing container/query/delete_item patterns (research.md Decisions 1–2) with no new abstraction layer; orchestration lives at the existing API-handler-composition level (research.md Decision 6). Unpublish's availability check is computed live rather than stored, avoiding a second, driftable copy of state (research.md Decision 3). No trash/undo/soft-delete mechanism is built for delete, since none was requested and the spec explicitly treats it as irreversible.

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A — This feature makes no LLM calls; no prompt/response/token/cost telemetry applies. Existing structured logging conventions (e.g. `StoryService`'s `logger.info` on `create_story`) are followed for the delete action and its cascade.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — Reuses `CosmosService`'s existing Managed Identity authentication; no new credential or connection type introduced.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET — The new delete confirmation dialog reuses the existing `role="dialog"`/`aria-modal`/`aria-labelledby` pattern from `StoryPublishActions.jsx`'s unpublish dialog (research.md Decision 7) rather than a one-off modal or `window.confirm()`; the greyed-out list row and the two play-surface notices reuse existing design tokens (`.text-muted`, existing `tag`/`btn` classes) rather than introducing new ones.

### Principle IX – Playtesting-Driven Quality (Post-Ship Verification, Non-Blocking)
**Status**: ✓ MET — Per the current constitution (v2.3.0), user acceptance verification is non-blocking; this feature is complete once its automated tests pass and it merges through the CI gate. No pre-implementation sign-off is required.

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: ✓ MET — No new PII is introduced or recorded; deletion removes data rather than adding any identity-attributed record.

### Principle XI – Implementer Design Latitude (Non-Blocking)
**Status**: ✓ MET — No pre-implementation design sign-off is required or sought; the delete control's exact placement/copy, and the greyed-out row's exact visual treatment, are left to the implementer within Principle VIII's constraints, following `005`'s established shared-control precedent.

### Principle XII – Right-Sized Scope — Not Enterprise-Grade (NON-NEGOTIABLE)
**Status**: ✓ MET — No new environment, identity federation, role hierarchy, undo/trash subsystem, or scaling infrastructure is introduced; no background job or push/real-time channel is added — availability is always computed live on an existing request path.

### Principle XIII – AI Agent Division of Labor (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A at planning time — Governs the GitHub-hosted handoff (PR creation, labelling, review, merge) rather than technical design; will be followed when this feature's implementation is pushed. No violation is introduced by this plan.

### Security & Access Control Requirements (constitution, non-principle section)
**Status**: ✓ MET — No secrets introduced; delete is only reachable by an authenticated, allow-listed Administrator.

### Screen contracts (constitution, UI Design System Requirements)
**Status**: ✓ MET, no amendment needed — research.md Decision 8: this extends the existing "Administrator — stories & configuration" screen contract's story list with one more per-row action, and the existing `Adventure select`/`Play surface` contracts with new states rather than new screens, the same kind of addition `005-story-publishing-done` already made for publish/unpublish.

No unjustified violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/025-story-delete/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout (`src/backend/` Python Azure Functions + `src/frontend/` React SPA). This feature extends the existing `Story`/`PlaySession` services, the existing administrator story list, and the existing play surface / in-progress-games list; it does not introduce a new container, service module, or page.

```text
src/backend/
├── services/
│   ├── story_service.py                         # MODIFY: add delete_story(story_id) -> bool
│   └── play_session_service.py                  # MODIFY: add delete_active_sessions_for_adventure(adventure_id) -> int
│                                                 #   (delete cascade, research.md Decision 2); add a shared
│                                                 #   "is this session's story still available?" check, raising a
│                                                 #   new StoryUnpublishedError alongside the existing
│                                                 #   AdventureNotFoundError, called from submit_interaction,
│                                                 #   resume_session, and get_session_detail_for_player
│                                                 #   (research.md Decision 4); extend list_player_sessions to
│                                                 #   surface `available: bool` per row from each row's current
│                                                 #   Story.published (research.md Decision 5)
├── api/
│   ├── admin/
│   │   └── stories.py                           # MODIFY: add delete_story handler, composing
│   │                                             #   StoryService.delete_story + PlaySessionService.
│   │                                             #   delete_active_sessions_for_adventure
│   └── game/
│       └── sessions.py                          # MODIFY: submit_interaction/resume_session/session-detail map
│                                                 #   SessionNotFoundError + AdventureNotFoundError to
│                                                 #   404 story_deleted, and the new StoryUnpublishedError to
│                                                 #   409 story_unpublished (contracts/api.md); list response
│                                                 #   passes through the new `available` field
├── function_app.py                              # MODIFY: register DELETE manage/stories/{storyId}
└── tests/
    ├── unit/
    │   ├── test_story_service.py                # MODIFY: delete_story (found/not-found) cases
    │   └── test_play_session_service.py         # MODIFY: delete_active_sessions_for_adventure (active
    │                                             #   removed, concluded untouched, multiple players);
    │                                             #   the story-unpublished check leaves the session
    │                                             #   unmodified; list_player_sessions' available field
    └── integration/
        ├── test_admin_stories_delete_endpoint.py # NEW: full delete lifecycle via HTTP (200, cascade,
        │                                         #   404 on repeat, published-state independence)
        └── test_game_sessions_endpoint.py        # MODIFY: story_deleted (404) and story_unpublished (409)
                                                    #   response bodies; list `available` field after
                                                    #   unpublish and after re-publish

src/frontend/
├── src/
│   ├── components/
│   │   ├── Admin/
│   │   │   └── StoryDeleteAction.jsx            # NEW: delete button + distinct destructive
│   │   │                                         #   confirmation dialog (FR-002), mirroring
│   │   │                                         #   StoryPublishActions.jsx's dialog pattern
│   │   └── GameSetup/
│   │       └── SavedGameRow.jsx                 # MODIFY: render a row with `available === false`
│   │                                             #   greyed out / non-continuable (FR-009) instead of
│   │                                             #   its normal Resume-button state
│   ├── hooks/
│   │   └── useDeleteStory.js                    # NEW: mirrors usePublishToggle.js's
│   │                                             #   status/confirmation state machine
│   ├── pages/
│   │   ├── AdminPage.jsx                        # MODIFY: render StoryDeleteAction per row; remove
│   │   │                                         #   the row from state on success (FR-012)
│   │   └── PlayPage.jsx                         # MODIFY: add story_deleted (404) and story_unpublished
│   │                                             #   (409) notice branches, each with a "return to your
│   │                                             #   list" action, alongside the existing branches
│   └── services/
│       └── storyDraftService.js                 # MODIFY: add deleteStory(token, storyId)
└── tests/
    ├── components/
    │   ├── StoryDeleteAction.test.jsx             # NEW: mirrors StoryPublishActions.test.jsx
    │   └── GameSetup/
    │       └── StoriesInProgress.test.jsx         # MODIFY: greyed-out row rendering for
    │                                               #   available === false, restored on re-publish
    ├── integration/
    │   └── admin_stories_list_delete.test.jsx     # NEW: mirrors admin_stories_list_publish.test.jsx —
    │                                               #   confirm dialog, row removal after delete
    └── Play/
        └── PlayPage.test.jsx                      # MODIFY: story_deleted and story_unpublished notice
                                                     #   rendering
```
