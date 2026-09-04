# Implementation Plan: Story Publishing

**Branch**: `005-story-publishing` | **Date**: 2026-08-30 | **Spec**: `specs/005-story-publishing/spec.md`

**Input**: Feature specification from `/specs/005-story-publishing/spec.md`

## Summary

Give a `Story` document an explicit `published` boolean (already defined by `004-story-creation-done`'s data model, defaulting to `false`) and add the two administrator-facing actions that flip it: `publish` and `unpublish`, each idempotent, each reachable from both the story-authoring wizard's new "Publish & assign" step and (once built) `012-story-editing-and-review`'s story list. Publishing is blocked unless a test-play gate (owned by `017-story-publish-test-play-gate`) is satisfied; this plan adds the two Story fields that gate reads (`contentUpdatedAt`, `lastTestPlayedAt`) and the read-side check itself, without building 017's own tracking UI/logic. A successful publish also stamps `lastPublishedAt`, retained across a later unpublish (FR-012). Unpublishing requires a client-side confirmation step only (FR-013) — no new server-side precondition beyond the existing "story exists" check.

**Sequencing note**: `004-story-creation-done` (the `Story` model, `story_service.py`, `api/manage/stories.py`, and the wizard shell) is fully planned but not yet implemented in code (`src/backend/models/story.py` etc. do not exist yet). This plan's contracts and file list assume `004`'s planned shapes as documented in its `data-model.md`/`contracts/api.md`, and its own tasks/implementation must land after (or together with) `004`'s.

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 18 via Vite (frontend, existing)

**Primary Dependencies**: No new dependencies — reuses `004-story-creation-done`'s planned `story_service.py`/Cosmos access pattern (`azure-cosmos` via `CosmosService`, already in use elsewhere) and the existing `authorize_admin` middleware.

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — the existing `stories` container (defined in `004-story-creation-done`'s data-model.md); this feature adds three fields to the `Story` document (`lastPublishedAt`, `contentUpdatedAt`, `lastTestPlayedAt`) rather than a new container.

**Testing**: pytest (backend `src/backend/tests/unit`, `src/backend/tests/integration`, existing convention); Vitest + React Testing Library (frontend `src/frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `src/backend/` + `src/frontend/` structure)

**Performance Goals**: N/A — publish/unpublish is a single low-frequency administrator action with no stated throughput/latency target (Principle IV)

**Constraints**: No per-player/per-group targeting capability (FR-009, explicit exclusion); no scheduled/future-dated publishing (Assumptions); the test-play gate (FR-008) is read-only from this feature's side — `017-story-publish-test-play-gate` owns writing `lastTestPlayedAt`, and until that feature ships, every publish attempt is correctly blocked (the field is always null), which is the safe and spec-correct interim state rather than a workaround

**Scale/Scope**: Same small administrator population as `003-account-provisioning-done`/`004-story-creation-done`; one new wizard step tab, two new API endpoints, one new reusable frontend action (usable from the wizard now and from `012`'s story list once it exists)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-007 enumerates every distinct publishing outcome needing a test (publish, unpublish, redundant publish, redundant unpublish, unpublish-with-active-sessions); contracts/api.md gives concrete request/response shapes for those tests to assert against, plus the FR-008 gate-blocked/gate-allowed paths.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — Both new endpoints (`publish`, `unpublish`) are gated by the existing `authorize_admin` middleware; no anonymous access.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model; extends the existing Python/Azure Functions + React stack.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — This plan does not build `017`'s test-play tracking UI or `012`'s story list; it adds only the two data fields (`contentUpdatedAt`, `lastTestPlayedAt`) those future features need to read/write, and a read-side gate check against them. No speculative assignment/targeting model is built (FR-009 explicitly excludes it).

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A — This feature makes no LLM calls; no prompt/response/token/cost telemetry applies. Existing structured logging conventions (see `authorize_admin` call sites) are followed for the publish/unpublish actions.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — Reuses `CosmosService`'s existing Managed Identity authentication; no new credential or connection type introduced.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET — The new "Publish & assign" wizard step tab reuses the existing step-tab shell and design-token primitives (`.btn*`, `.field`) established by `004-story-creation-done`'s `AdminStoryWizardPage.jsx`; the unpublish confirmation (FR-013) uses the design system's existing dialog/confirmation primitive rather than a one-off modal. No new colors, fonts, or spacing values are introduced.

### Principle IX – User-Verified Acceptance Before Completion (NON-NEGOTIABLE)
**Status**: ✓ MET — This feature's task list (Phase 2) will end with an explicit final acceptance task verified by the requesting user/product owner against the deployed environment, per the constitution's standing requirement.

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: ✓ MET — Per FR-012, `lastPublishedAt` records only a timestamp, explicitly with **no** administrator-identity attribution; no PII is introduced by this feature.

### Security & Access Control Requirements (constitution, non-principle section)
**Status**: ✓ MET — No secrets introduced; publish/unpublish state is only reachable by an authenticated, allow-listed Administrator.

No unjustified violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/005-story-publishing/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout (`src/backend/` Python Azure Functions + `src/frontend/` React SPA). This feature extends `004-story-creation-done`'s planned `Story` model/service and wizard shell; it does not introduce a new container, service module, or page.

```text
src/backend/
├── models/
│   └── story.py                                 # MODIFY (as introduced by 004): add lastPublishedAt,
│                                                 #   contentUpdatedAt, lastTestPlayedAt fields
├── services/
│   └── story_service.py                         # MODIFY (as introduced by 004): add publish(story_id),
│                                                 #   unpublish(story_id), and the FR-008 gate check
├── api/
│   └── manage/
│       └── stories.py                           # MODIFY (as introduced by 004): add publish_story,
│                                                 #   unpublish_story handlers
├── function_app.py                              # MODIFY: register the two new routes
└── tests/
    ├── unit/
    │   └── test_story_service.py                # MODIFY: publish/unpublish, idempotency, gate
    │                                             #   blocked/allowed cases (depends on 004's file)
    └── integration/
        └── test_admin_stories_publish_endpoint.py # NEW: full publish/unpublish lifecycle via HTTP,
                                                    #   including the blocked-with-explanation case

src/frontend/
├── src/
│   ├── components/
│   │   └── Admin/
│   │       └── StoryWizard/
│   │           └── StepPublish.jsx              # NEW: "Publish & assign" step — publish button,
│   │                                             #   blocked-explanation text (FR-011), unpublish
│   │                                             #   button + confirmation dialog (FR-013)
│   ├── pages/
│   │   └── AdminStoryWizardPage.jsx             # MODIFY (as introduced by 004): add the fifth/sixth
│   │                                             #   step tab wiring to StepPublish
│   └── services/
│       └── storyDraftService.js                 # MODIFY (as introduced by 004): add publishStory,
│                                                 #   unpublishStory calls
└── tests/
    ├── components/
    │   └── StoryWizard/
    │       └── StepPublish.test.jsx             # NEW
    └── integration/
        └── admin_story_publish_flow.test.jsx    # NEW: publish blocked → (simulated gate satisfied) →
                                                  #   publish succeeds → unpublish with confirmation
```

Note: `012-story-editing-and-review`'s story-list entry point for this same publish/unpublish action (FR-010) is not built by this plan — that screen does not exist yet (per spec.md's Design Reference note) and is `012`'s own scope; it will call the same `publish`/`unpublish` endpoints this plan adds.

## Post-Design Constitution Check

*Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md).*

No new violations surfaced during design. One item worth confirming explicitly:

- **Principle IV (YAGNI)**: `data-model.md` adds `contentUpdatedAt` to `Story` now, stamped at creation and on every future content-changing save, even though no content-editing feature (`012`) exists yet to update it post-creation. This is not premature: FR-008's gate is meaningless without a "content last changed" timestamp to compare against, and `004`'s creation path is the natural, minimal place to stamp its initial value (equal to `createdAt`). `012` will update it on edit; this plan does not build `012`'s edit path itself. Still ✓ MET.

Constitution Check gate: **PASS**. Proceed to `/speckit-tasks`.
