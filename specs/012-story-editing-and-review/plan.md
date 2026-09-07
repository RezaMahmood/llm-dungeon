# Implementation Plan: Story Editing and Review

**Branch**: `012-story-editing-and-review` | **Date**: 2026-09-06 | **Spec**: [`specs/012-story-editing-and-review/spec.md`](./spec.md)

**Input**: Feature specification from `/specs/012-story-editing-and-review/spec.md`

## Summary

Give administrators the maintenance half of story authoring: a story list that shows
published status and exposes publish/unpublish (`005` FR-010), a read-only viewer of a
story's complete configuration file, a download of that same file, a re-upload that
overwrites the story it came from (or creates a new one when its `id` is removed), and the
existing story wizard reopened in "edit" mode against a saved story.

Technically this is four backend endpoints and two frontend screens on top of what already
exists. One new module (`story_config_file.py`) owns the canonical serialization, so the
viewer, the download, and the importer are all the same bytes (FR-002/SC-001). Edit mode
reuses the wizard verbatim by seeding a `StoryDraft` from the story (`sourceStoryId`,
`baseContentVersion`), which is what makes the per-field one-shot `Suggest` action "exactly
as in creation" without a second LLM surface. Stale-save rejection (FR-006) uses a new
`Story.contentVersion` counter — deliberately not the Cosmos `_etag`, so a publish from the
list never turns the next content save into a false conflict. FR-010 (no per-session
configuration snapshot) needs no code: `PlaySessionService` already re-reads the story every
turn; this plan pins that with a regression test.

**Sequencing note**: `011-story-import` is spec-only today, and `012` FR-005/FR-008 put
re-upload inside this feature's scope. This plan therefore builds the file format, the
validator, and the create-or-overwrite import endpoint **here**, conforming to `011`'s
FR-002/003/004/005/006/007 rather than defining separate rules (research.md §1).
`011-story-import` should be re-scoped, when it is planned, to its own entry surface and any
extra acceptance coverage on top of this mechanism — it MUST NOT define a second format or
validator. `010-story-test-play`/`017-story-publish-test-play-gate` remain unimplemented;
this feature only re-arms their gate implicitly by stamping `contentUpdatedAt`, which
`StoryService.can_publish` already reads.

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 19 via Vite (frontend, existing)

**Primary Dependencies**: None new. Backend reuses `azure-cosmos` via `CosmosService`, the existing `authorize_admin` middleware, `StoryDraftService`/`StoryService`, and `LLMService.generate_story_config`; frontend reuses `axios`, `react-router-dom` v7, MSAL, and the vendored design-token stylesheet.

**Storage**: Azure Cosmos DB serverless — existing `stories` and `storyDrafts` containers. No new container. Two fields are added to `Story` (`lastUpdatedBy`, `contentVersion`) and two nullable fields to `StoryDraft` (`sourceStoryId`, `baseContentVersion`); both are read with defaults so rows written before this feature keep loading (the `contentUpdatedAt` precedent in `Story.from_dict`).

**Testing**: pytest (`src/backend/tests/unit`, `src/backend/tests/integration`) against the existing in-memory Cosmos/LLM stubs; Vitest + React Testing Library (`src/frontend/tests`). No live Azure resource is required by any test (Principle I).

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `src/backend/` + `src/frontend/`)

**Performance Goals**: N/A — every action here is a single low-frequency administrator operation with no stated throughput or latency target (Principle IV)

**Constraints**: The viewer and the download must be byte-identical (FR-002/SC-001), which forces one serializer and a raw-text transport on the client; a re-upload must never write `published` (FR-007); the downloaded file must contain no administrator identity (FR-004, Principle X); the new screens ship unstyled by explicit user decision (FR-012 — see the Principle VIII exception below); no version history and no field-level merge (spec Assumptions). The viewer renders an arbitrarily long file, so its `<pre>` lives in its own `overflow: auto` scroll container (keyboard-focusable, so a keyboard-only administrator can scroll it) with `white-space: pre` preserved — the displayed text stays the file's exact bytes, and no long line or deep configuration forces a horizontal page scroll.

**Scale/Scope**: Same small administrator population as `003`/`004`/`005`. Four new endpoints, one new backend module, two modified models/services, two new frontend screens (story configuration viewer, wizard edit mode), one extracted shared component (publish actions), one new upload component.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Re-evaluated after Phase 1 design (2026-09-06): unchanged — one explicit, justified exception under Principle VIII (FR-012), recorded in Complexity Tracking. No other violations.**

**Re-checked after cross-artifact analysis (2026-09-07)**: the analysis found the configuration viewer to be a screen traceable to no screen contract, which Governance forbids shipping. Resolved by amending the constitution to v2.3.0 with an "Administrator — stories & configuration" screen contract rather than by taking a second exception — see the Governance subsection below. The Principle VIII styling exception is unchanged and remains the only exception this feature carries.

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-008 enumerates every maintenance action needing a test; quickstart.md's scenario table maps each of the 17 required behaviors (including the rejected stale save, the id-less upload, the unmatched-`id` rejection, and the in-flight-session regression) to a named test file. All tests run locally against the existing in-memory Cosmos and LLM stubs — no live Azure dependency, no manual step.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — All four new endpoints go through the existing `authorize_admin` middleware; the configuration endpoint is a normal authenticated API call, and the download is a client-side blob built from that authenticated response (research.md §10) rather than an anonymously reachable file URL.

### Principle III – Defined Technology Stack
**Status**: ✓ MET — No new language, framework, or hosting model; Python/Azure Functions + React 19 SPA throughout, no new runtime dependency in either `requirements.txt` or `package.json`.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — No new container, no version history, no field-level merge UI, no `schemaVersion` marker on the file format (research.md §3), no change-detection optimization on `narrativeGuidance` regeneration (§5). Edit mode is two nullable fields on the existing draft rather than a new entity, and FR-010 is satisfied by existing behavior with a regression test instead of new code (§9).

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — All new tests land in the existing pytest and Vitest suites already wired into the PR gate; nothing here needs a new workflow.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET — The two LLM paths this feature touches (`Suggest` via the draft exchange, `narrativeGuidance` regeneration on save/import) both go through `LLMService`, which already emits prompt/response/token/cost/latency telemetry. New routes are registered through `function_app.py`'s `_guarded` wrapper, keeping `http.route` a low-cardinality template.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — All persistence goes through `CosmosService`'s existing Managed Identity (`DefaultAzureCredential`) path; no key, connection string, or new network path is introduced.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ⚠️ **EXPLICIT, JUSTIFIED EXCEPTION** (see Complexity Tracking) — Per spec FR-012 and the 2026-09-06 clarification, this feature's two new screens (story list additions and the configuration viewer) ship as plain, unstyled pages with no visual design pass. The exception is narrow: they are built **only** from existing design-system classes (`.table`, `.tag`, `.btn*`, `.field`, `.hr`, `.dialog*`) and token-based inline styles, introducing **no** off-system color, font, spacing, or radius value and **no** parallel reimplementation of an existing control — the publish/unpublish control is *extracted* from `StepPublish.jsx` into a shared component rather than rebuilt (research.md §11). The accessibility bar is **not** part of the exception and applies in full: semantic headings, real labelled controls, keyboard operability, visible focus, meaningful button text, and status conveyed by text as well as color. The wizard reached via FR-003 keeps `004`'s existing styling.

### Principle IX – Playtesting-Driven Quality (Post-Ship Verification, Non-Blocking)
**Status**: ✓ MET — Completion is gated on the automated suites and CI only. quickstart.md's manual walkthrough is explicitly marked informational and non-blocking; `tasks.md` MUST NOT add a blocking human-acceptance gate for this feature (no high-risk area is opted back in).

### Principle X – PII Protection by Design (NON-NEGOTIABLE)
**Status**: ✓ MET — `lastUpdatedBy` stores the administrator's `oid`, never an email, matching `createdBy`; and FR-004 keeps both identities out of the downloaded file entirely, so no PII leaves the access-controlled store in an artifact an administrator can mail around. No PII enters logs, telemetry, commit messages, or the PR.

### Principle XI – Implementer Design Latitude (Non-Blocking)
**Status**: ✓ MET — No pre-implementation design sign-off task is required or included; implementation proceeds on the implementer's judgment within Principle VIII's constraints as narrowed by the FR-012 exception above.

### Principle XII – Right-Sized Scope — Not Enterprise-Grade (NON-NEGOTIABLE)
**Status**: ✓ MET — No new environment, identity federation, role hierarchy, or scaling infrastructure. Concurrency control is one integer plus the `_etag` guard already used in `play_session_service.py` — not a locking or revision-history subsystem — and conflicts are surfaced for the administrator to reapply by hand rather than merged (spec Assumptions).

### Principle XIII – AI Agent Division of Labor (NON-NEGOTIABLE)
**Status**: ✓ MET / N/A at planning time — Spec work stays local; when implementation is ready this agent pushes the branch and opens the PR labelled `AI Generated` + `Claude`, with a Conventional-Commits title (`feat(backend)`/`feat(frontend)` scope per `scripts/pr-title-config.js`), without auto-merge. Copilot reviews; the requesting user merges.

### Governance – Screen contract traceability & the layout/scroll contract
**Status**: ✓ MET (as of the 2026-09-07 amendment) — Governance requires every shipped screen to be traceable to a screen contract or a documented amendment extending one, and requires this analysis to treat a contradiction with the layout/scroll contract as blocking. Both are now addressed:

- **Traceability**: constitution v2.3.0 adds the **Administrator — stories & configuration** screen contract, covering this feature's two screens (the story list with status and publish/unpublish entry point, and the read-only configuration viewer with its download). That section now also states explicitly that a contract may exist without a prototype screen when a spec defers visual design, which is exactly FR-012's case; `specs/designs/README.md` points at it. The deferral covers styling only — it does not weaken the contract's required affordances.
- **Layout/scroll**: the fixed-viewport shell (contract rule 1) is a *play-surface* rule in this codebase — `src/frontend/src/index.css` deliberately carries no page-wide `overflow: hidden`, with a recorded reason (it clipped the wizard's growing World & setting step). The viewer therefore does not introduce a page-level scroll rule; instead its `<pre>` sits in its own keyboard-focusable `overflow: auto` container, so a long configuration scrolls inside the screen rather than breaking the page horizontally (see Constraints, task T020).

### Security & Access Control / PII & Data Protection / Observability sections
**Status**: ✓ MET — No secret is introduced; the story configuration file contains no credential and no PII; new endpoints inherit the existing admin allow-list check and telemetry wrapper.

## Project Structure

### Documentation (this feature)

```text
specs/012-story-editing-and-review/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output — 12 decisions
├── data-model.md        # Phase 1 output — Story/StoryDraft changes + the config file
├── quickstart.md        # Phase 1 output — how to run and prove it
├── contracts/
│   └── api.md           # Phase 1 output — 4 new endpoints + 2 modified
├── checklists/
│   └── requirements.md  # Pre-existing
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by this command)
```

### Source Code (repository root)

**Structure Decision**: The existing web-application layout (`src/backend/` Python Azure
Functions + `src/frontend/` React SPA). This feature adds one backend module, two frontend
pages/components, and modifies the story model/service/API established by
`004-story-creation-done` and `005-story-publishing-done`. No new container, no new service
boundary.

```text
src/backend/
├── models/
│   ├── story.py                                     # MODIFY: add lastUpdatedBy, contentVersion
│   │                                                #   (+ to_dict/from_dict with back-compat defaults)
│   └── story_draft.py                               # MODIFY: add sourceStoryId, baseContentVersion
├── services/
│   ├── story_config_file.py                         # NEW: canonical serialize() + parse()/validate()
│   │                                                #   for the Story Configuration File
│   ├── story_service.py                             # MODIFY: apply_content_write() (preserve/replace/
│   │                                                #   stamp/version), import_configuration(),
│   │                                                #   StaleStoryError
│   └── story_draft_service.py                       # MODIFY: create_edit_draft(story),
│                                                     #   save_draft_to_story(draft_id), draft-mode guards
├── api/
│   └── admin/
│       └── stories.py                               # MODIFY: get_story_configuration, create_edit_draft,
│                                                     #   save_draft, import_story handlers; contentVersion
│                                                     #   surfaced by the existing get_story response; and
│                                                     #   generate_story_from_draft rejects an edit draft
│                                                     #   with 422 wrong_draft_mode (contracts/api.md)
├── function_app.py                                  # MODIFY: register the 4 new routes
└── tests/
    ├── conftest.py                                  # MODIFY: shared `_story(**overrides)` factory
    ├── unit/
    │   ├── test_models.py                           # MODIFY: new Story/StoryDraft field defaults
    │   ├── test_story_config_file.py                # NEW: serialization exactness, excluded fields,
    │   │                                             #   every validation rejection reason
    │   ├── test_story_service.py                    # MODIFY: content write preserves/stamps/versions,
    │   │                                             #   published untouched, gate re-armed
    │   ├── test_story_draft_service.py              # MODIFY: edit-draft seeding, save, stale save,
    │   │                                             #   wrong-draft-mode guards
    │   └── test_play_session_service.py             # MODIFY: FR-010 regression — no session snapshot
    └── integration/
        ├── test_admin_stories_endpoint.py             # MODIFY: get_story exposes contentVersion,
        │                                              #   lastUpdatedBy
        ├── test_admin_story_configuration_endpoint.py # NEW: viewer/download bytes, 404, authz
        ├── test_admin_story_edit_endpoint.py          # NEW: edit-draft → save, 409 stale, 422 not_ready
        └── test_admin_story_import_endpoint.py        # NEW: overwrite, new-story, confirmation/title/
                                                        #   unmatched-id/invalid rejections

src/frontend/
├── src/
│   ├── App.jsx                                      # MODIFY: routes /admin/stories/:storyId and
│   │                                                 #   /admin/stories/:storyId/edit (lazy, admin-gated)
│   ├── pages/
│   │   ├── AdminPage.jsx                            # MODIFY: view/edit links, publish actions (FR-011),
│   │   │                                             #   upload control
│   │   ├── AdminStoryConfigurationPage.jsx          # NEW: read-only viewer + Download (FR-002, FR-004)
│   │   └── AdminStoryWizardPage.jsx                 # MODIFY: edit mode — seed from story, "Save changes",
│   │                                                 #   stale-save message
│   ├── components/Admin/
│   │   ├── StoryPublishActions.jsx                  # NEW (extracted from StepPublish): shared publish/
│   │   │                                             #   unpublish + confirm dialog
│   │   ├── StoryConfigUpload.jsx                    # NEW: file picker, overwrite confirmation, title
│   │   │                                             #   prompt, rejection messages
│   │   └── StoryWizard/StepPublish.jsx              # MODIFY: render the extracted component
│   └── services/
│       └── storyDraftService.js                     # MODIFY: getStoryConfiguration (raw text),
│                                                     #   createEditDraft, saveDraftToStory,
│                                                     #   importStoryConfiguration
└── tests/
    ├── components/
    │   ├── StoryPublishActions.test.jsx             # NEW
    │   └── StoryConfigUpload.test.jsx               # NEW
    └── integration/
        ├── admin_stories_list.test.jsx              # MODIFY: status + publish from the list (FR-001/011)
        ├── admin_story_publish_flow.test.jsx        # MODIFY: list entry point parity with the wizard
        ├── admin_story_configuration_view.test.jsx  # NEW: viewer text == downloaded text
        ├── admin_story_edit_flow.test.jsx           # NEW: reopen, Suggest, save, stale-save message
        └── admin_story_import_flow.test.jsx         # NEW: overwrite confirm, id-less + title, rejections
```

## Complexity Tracking

> Filled because the Constitution Check records one explicit exception (Principle VIII).
> Screen-contract traceability was resolved by amending the constitution (v2.3.0), not by a
> second exception, so it is not tracked here.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Principle VIII: the story list additions and the configuration viewer ship with no visual design pass (spec FR-012) | Directly requested by the user on 2026-09-06 to keep MVP velocity; Principle VIII itself permits "an explicit, justified exception" recorded in the plan's Constitution Check, and the spec's Assumptions require this plan to record it here rather than claim the requirement is satisfied | Doing a full design pass now was rejected by the requesting user as work that does not move the MVP; and shipping *nothing* until it is styled would block the maintenance workflow that FR-001/FR-002 exist to provide. The exception is bounded so nothing must later be undone: no off-system color/font/spacing values are introduced, only existing design-system classes and token-based styles are used, the publish control is extracted rather than duplicated, and the full accessibility bar (semantics, labels, keyboard, focus, non-color status) still applies. Visual styling is additive follow-up work. |
