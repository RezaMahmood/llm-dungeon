# Implementation Plan: Story Publishing

**Branch**: `005-story-publishing` | **Date**: 2026-08-30 | **Spec**: `specs/005-story-publishing/spec.md`

**Input**: Feature specification from `/specs/005-story-publishing/spec.md`

## Summary

Give a `Story` document an explicit `published` boolean (already defined by `004-story-creation-done`'s data model, defaulting to `false`) and add the two administrator-facing actions that flip it: `publish` and `unpublish`, each idempotent, each reachable from both the story-authoring wizard's new "Publish & assign" step and the administrator story list (which already exists at `src/frontend/src/pages/AdminPage.jsx`). Publishing is blocked unless a test-play gate (owned by `017-story-publish-test-play-gate`) is satisfied; this plan adds the two Story fields that gate reads (`contentUpdatedAt`, `lastTestPlayedAt`) and the read-side check itself, without building 017's own tracking UI/logic. A successful publish also stamps `lastPublishedAt`, retained across a later unpublish (FR-012). Unpublishing requires a client-side confirmation step only (FR-013) — no new server-side precondition beyond the existing "story exists" check.

**Sequencing note**: `004-story-creation-done` (the `Story` model, `story_service.py`, the admin story endpoints at `src/backend/api/admin/stories.py`, and the wizard shell) is now implemented in code. This plan's contracts and file list were originally written against `004`'s planned shapes (`data-model.md`/`contracts/api.md`); verified against the actual code during `/speckit-tasks`, the only drift is that the admin story endpoints live at `src/backend/api/admin/stories.py` (URL prefix `manage/stories`, per `function_app.py`'s route registration), not `src/backend/api/manage/stories.py` as originally assumed — `tasks.md` uses the correct path.

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 18 via Vite (frontend, existing)

**Primary Dependencies**: No new dependencies — reuses `004-story-creation-done`'s planned `story_service.py`/Cosmos access pattern (`azure-cosmos` via `CosmosService`, already in use elsewhere) and the existing `authorize_admin` middleware.

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — the existing `stories` container (defined in `004-story-creation-done`'s data-model.md); this feature adds three fields to the `Story` document (`lastPublishedAt`, `contentUpdatedAt`, `lastTestPlayedAt`) rather than a new container.

**Testing**: pytest (backend `src/backend/tests/unit`, `src/backend/tests/integration`, existing convention); Vitest + React Testing Library (frontend `src/frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `src/backend/` + `src/frontend/` structure)

**Performance Goals**: N/A — publish/unpublish is a single low-frequency administrator action with no stated throughput/latency target (Principle IV)

**Constraints**: No per-player/per-group targeting capability (FR-009, explicit exclusion); no scheduled/future-dated publishing (Assumptions); the test-play gate (FR-008) is read-only from this feature's side — `017-story-publish-test-play-gate` owns writing `lastTestPlayedAt`, and until that feature ships, every publish attempt is correctly blocked (the field is always null), which is the safe and spec-correct interim state rather than a workaround

**Scale/Scope**: Same small administrator population as `003-account-provisioning-done`/`004-story-creation-done`; one new wizard step tab, two new API endpoints, one reusable frontend publish/unpublish action shared by the wizard step and the existing administrator story list's per-row control

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-007 enumerates every distinct publishing outcome needing a test (publish, unpublish, redundant publish, redundant unpublish, unpublish-with-active-sessions); contracts/api.md gives concrete request/response shapes for those tests to assert against, plus the FR-008 gate-blocked/gate-allowed paths.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — Both new endpoints (`publish`, `unpublish`) are gated by the existing `authorize_admin` middleware; no anonymous access.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model; extends the existing Python/Azure Functions + React stack.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — This plan does not build `017`'s test-play tracking UI, and it does not build `012`'s full story-list/editing screen — it adds the per-row publish/unpublish action to the administrator story list that already exists (FR-010), which `012` later extends rather than replaces. It adds only the two data fields (`contentUpdatedAt`, `lastTestPlayedAt`) those future features need to read/write, and a read-side gate check against them. No speculative assignment/targeting model is built (FR-009 explicitly excludes it).

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A — This feature makes no LLM calls; no prompt/response/token/cost telemetry applies. Existing structured logging conventions (see `authorize_admin` call sites) are followed for the publish/unpublish actions.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — Reuses `CosmosService`'s existing Managed Identity authentication; no new credential or connection type introduced.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET — The new "Publish & assign" wizard step tab reuses the existing step-tab shell and design-token primitives (`.btn*`, `.field`) established by `004-story-creation-done`'s `AdminStoryWizardPage.jsx`; the unpublish confirmation (FR-013) uses the design system's existing dialog/confirmation primitive rather than a one-off modal. No new colors, fonts, or spacing values are introduced.

### Principle IX – Playtesting-Driven Quality (Post-Ship Verification, Non-Blocking)
**Status**: ✓ MET — **Revised 2026-09-06**: the constitution was relaxed to v2.0.0, renaming this principle and making user verification explicitly *non-blocking* — a feature is complete once its automated tests pass and it merges through the CI gate. This plan was originally written against the previous "User-Verified Acceptance Before Completion (NON-NEGOTIABLE)" wording, and `tasks.md`'s T018 reflects that older gate (it was satisfied on 2026-09-05 regardless). No acceptance sign-off task is required for the Phase 5 convergence work; design and flow issues are expected to surface through playtesting and are fixed as follow-up work.

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: ✓ MET — Per FR-012, `lastPublishedAt` records only a timestamp, explicitly with **no** administrator-identity attribution; no PII is introduced by this feature.

### Principle XI – Implementer Design Latitude (Non-Blocking)
**Status**: ✓ MET — **Revised 2026-09-06**: the constitution was relaxed to v2.0.0, replacing the former "UI Design Pre-Agreement Before Implementation (NON-NEGOTIABLE)" with implementer design latitude: a pre-implementation design sign-off is NOT required and MUST NOT be used to block implementation. `tasks.md`'s Phase 0 (T000) reflects the older gate and is retained as completed history; it does **not** gate the Phase 5 convergence work, which proceeds directly to implementation using the existing design system. Principle VIII still binds every new control (the story list's per-row publish/unpublish action included) to this project's design-token layer, interaction states, and accessibility bar.

### Principle XII – Right-Sized Scope — Not Enterprise-Grade (NON-NEGOTIABLE)
**Status**: ✓ MET — No new environment, identity federation, role hierarchy, or scaling infrastructure is introduced; publish/unpublish is a single boolean flip plus a timestamp, gated by the existing `authorize_admin` allow-list check already used elsewhere.

### Principle XIII – AI Agent Division of Labor (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A at planning time — This principle governs the GitHub-hosted handoff (PR creation, labelling, review, merge) rather than the technical design; it will be followed when this feature's implementation is pushed and its PR opened (local agent opens the PR labelled `AI Generated`/`Claude`, does not enable auto-merge, GitHub Copilot reviews, the requesting user merges manually). No violation is introduced by this plan.

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
│   └── admin/
│       └── stories.py                           # MODIFY (as introduced by 004; URL prefix is manage/stories,
│                                                 #   file path is api/admin/ — see Sequencing note): add publish_story,
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
│   │   ├── AdminStoryWizardPage.jsx             # MODIFY (as introduced by 004): add the fifth/sixth
│   │   │                                         #   step tab wiring to StepPublish
│   │   └── AdminPage.jsx                        # MODIFY (as introduced by 004, Phase 5): add the
│   │                                             #   per-row publish/unpublish action, FR-011
│   │                                             #   explanatory text, FR-013 confirmation, and
│   │                                             #   FR-016 in-place row update to the story list
│   └── services/
│       └── storyDraftService.js                 # MODIFY (as introduced by 004): add publishStory,
│                                                 #   unpublishStory calls
└── tests/
    ├── components/
    │   └── StoryWizard/
    │       └── StepPublish.test.jsx             # NEW
    └── integration/
        ├── admin_story_publish_flow.test.jsx    # NEW: publish blocked → (simulated gate satisfied) →
        │                                         #   publish succeeds → unpublish with confirmation
        └── admin_stories_list.test.jsx          # MODIFY (as introduced by 004, Phase 5): list-side
                                                  #   publish/unpublish coverage (FR-007)
```

Note: FR-010's story-list entry point **is** built by this plan (revised 2026-09-06 — see the Scope Revision below). It is added to the administrator story list that already exists at `src/frontend/src/pages/AdminPage.jsx`, calling the same `publish`/`unpublish` endpoints and reusing the same frontend action as the wizard step, so there is exactly one publish path. `012-story-editing-and-review` extends that list with its own editing/review capabilities rather than building a second story-list screen or a second publish path.

## Scope Revision (2026-09-06)

The `/speckit-clarify` session of 2026-09-06 moved FR-010's story-list entry point **into this
feature's scope**; it had previously been deferred to `012-story-editing-and-review`. Two facts
drove the change: the administrator story list already exists (`src/frontend/src/pages/AdminPage.jsx`,
rendering each story's name and published status), and `012` is not yet started, so leaving FR-010 to
it would ship this feature with a stated requirement unmet and no way to publish an already-generated
story outside the creation wizard.

What this does **not** change: no backend, endpoint, data-model, or contract change is required — the
`publish`/`unpublish` endpoints, the FR-008 gate, and `storyDraftService`'s `publishStory`/`unpublishStory`
were all delivered in Phases 1–4 and already satisfy FR-015 server-side (both re-read the story from
storage and evaluate the gate against stored state, trusting nothing the client's view was showing).
The remaining work is confined to the frontend list UI and its tests.

Sequencing: this revision is delivered as `tasks.md`'s **Phase 5: Convergence** (T019–T024), which runs
after Phase 4 and depends on Phase 3's endpoints and service actions already being in place. It is
additive — no Phase 1–4 task is re-opened, and no already-shipped behavior changes.

Newly in scope (spec FR-010, FR-011, FR-013, FR-014, FR-015, FR-016, US1/AC4, SC-005):

- a per-row, single-story publish/unpublish control in the existing story list (no multi-select, no bulk);
- the same FR-013 confirmation before unpublishing, and the same FR-011 explanatory text on a
  gate-blocked publish, both shared with `StepPublish.jsx` rather than reimplemented;
- an in-place row update from the response, with no full list reload and no staleness/conflict error.

Still out of scope and owned by other features: `012`'s editing, full-configuration view, download and
re-upload capabilities; `017-story-publish-test-play-gate`'s writing of `lastTestPlayedAt`.

## Post-Design Constitution Check

*Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md).*

No new violations surfaced during design. One item worth confirming explicitly:

- **Principle IV (YAGNI)**: `data-model.md` adds `contentUpdatedAt` to `Story` now, stamped at creation and on every future content-changing save, even though no content-editing feature (`012`) exists yet to update it post-creation. This is not premature: FR-008's gate is meaningless without a "content last changed" timestamp to compare against, and `004`'s creation path is the natural, minimal place to stamp its initial value (equal to `createdAt`). `012` will update it on edit; this plan does not build `012`'s edit path itself. Still ✓ MET.

Constitution Check gate: **PASS**. Proceed to `/speckit-tasks`.
