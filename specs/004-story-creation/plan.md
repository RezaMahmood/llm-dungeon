# Implementation Plan: Story Creation

**Branch**: `004-story-creation` | **Date**: 2026-08-29 | **Spec**: `specs/004-story-creation/spec.md`

**Input**: Feature specification from `/specs/004-story-creation/spec.md`

## Summary

Give a signed-in Administrator a four-step wizard (name & cover, world & setting, tone & reading level, session length — reachable in any order, per the Clarifications and `specs/designs/04-admin-wizard.html`) in which they describe a story idea in plain language, are asked guiding questions to fill in the gaps, and define character types and completion criteria through dedicated fields. The moment the minimum required detail exists (a non-empty setting/plot description, at least one character type, at least one success condition), the backend calls the Azure AI Foundry deployed model to generate the story's narrative-consistency guidance and persists a complete, unpublished `Story` document — with no separate manual save step. Abandoning a session before that point leaves nothing persisted, guaranteed by a Cosmos TTL on the in-progress draft rather than application cleanup code.

**This is the first feature to make a real LLM call.** No prior spec (`002`, `003`) exercises `007-azure-infrastructure-provisioning`'s Azure AI Foundry resource, so this plan also stands up the shared LLM-calling and OpenTelemetry-observability infrastructure (Constitution Principle VI) that later features (`008-core-gameplay`, `010-story-test-play`, `011-story-import`) are expected to reuse rather than reinvent.

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 18 via Vite (frontend, existing)

**Primary Dependencies**:
- Backend (existing): `azure-functions`, `azure-cosmos`, `azure-identity`, `PyJWT[crypto]`, `python-dotenv`, `requests`
- Backend (new): `azure-ai-inference` — calls the Foundry-deployed model via Managed Identity (resolved in research.md §1); `azure-monitor-opentelemetry` — one-call OpenTelemetry→Application Insights wiring for Constitution Principle VI (resolved in research.md §2)
- Frontend (existing): React 18, `@azure/msal-browser`/`@azure/msal-react`, `axios`, `react-router-dom`

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — two new containers: `storyDrafts` (TTL-enabled, ephemeral session state) and `stories` (persisted, unpublished-by-default) (resolved in research.md §3, data-model.md)

**Testing**: pytest (backend `backend/tests/unit`, `backend/tests/integration`, existing convention, with the Foundry client mocked per research.md §1); Vitest + React Testing Library (frontend `frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`; LLM calls reach the Azure AI Foundry resource `007` provisions, over the same private-endpoint/Managed-Identity path as Cosmos DB

**Project Type**: Web application (existing `backend/` + `frontend/` structure)

**Performance Goals**: N/A — no throughput/latency target specified or needed (Principle IV); an LLM generation call is inherently seconds-scale and the wizard UI treats it as an async action with a loading state, not a request with a tight budget

**Constraints**: No resume-after-abandonment capability (explicit Assumption); no story-count limit; multiple concurrent drafts per administrator are explicitly permitted (Clarifications) so draft identity is per-session, not per-administrator

**Scale/Scope**: Same small administrator population as `003-account-provisioning`; one new wizard screen (four steps) plus the shared LLM/telemetry service layer

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-007 enumerates every distinct step needing a test (eliciting setting/plot, character types, completion criteria, generation, persistence, abandonment); contracts/api.md and data-model.md give concrete request/response and entity shapes for those tests to assert against, plus the new failure paths this plan introduces (malformed generation output, TTL expiry).

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — Every new endpoint (draft create/read/update, message exchange, story list/read) is gated by the existing `authorize_admin` middleware; no anonymous access to draft or story data.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model. `azure-ai-inference` and `azure-monitor-opentelemetry` are library additions within the existing Python/Azure Functions stack, not a stack deviation.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — Draft cleanup relies on a native Cosmos TTL rather than a custom cleanup job or explicit "abandon" endpoint (research.md §3); story/draft listing has no pagination at this project's stated scale; a single Foundry call pattern (`llm_service.py`) serves both the guiding-question exchange and the final generation, rather than two bespoke clients.

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI; no new CI configuration needed.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET — This plan is what *implements* Principle VI for the first time (research.md §2): every Foundry call (guiding-question exchange and final generation) is wrapped in an OpenTelemetry span carrying the full prompt, full response, input/output token counts, computed USD cost, and latency, exported to Application Insights via `azure-monitor-opentelemetry`, and attributable to its draft/session id.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — The Foundry client authenticates via `DefaultAzureCredential` (Managed Identity), matching `CosmosService`'s existing pattern; no API key or connection string is introduced. Private-endpoint enforcement itself is `007`'s network-layer responsibility; this plan introduces no code path that could bypass it (no direct public-endpoint fallback).

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET, with a gap noted — The wizard shell reuses `specs/designs/04-admin-wizard.html`'s step-tab layout and `frontend/src/styles/designTokens.css` tokens/primitives (`.field`, `.input`, `.btn*`). The new character-type/completion-criteria fields (FR-008) have no reference markup in the static mockup (research.md §5); they are built from the same design-token primitives as repeatable list rows, not new one-off component classes, consistent with the constitution's "no parallel, screen-specific reimplementation" rule.

### Security & Access Control Requirements (constitution, non-principle section)
**Status**: ✓ MET — No secrets introduced (Foundry auth is Managed Identity, per Principle VII); story/draft data is only ever reachable by an authenticated, allow-listed Administrator.

No unjustified violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-story-creation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout (`backend/` Python Azure Functions + `frontend/` React SPA, established by `002-login-and-access-control`). This feature adds a new service layer (LLM client + drafts + stories) under `backend/` and a new wizard screen under `frontend/`; it does not modify any file `002`/`003` own.

```text
backend/
├── config.py                                    # MODIFY: add STORY_DRAFTS_CONTAINER, STORIES_CONTAINER,
│                                                 #   AZURE_AI_FOUNDRY_ENDPOINT, LLM_*_TOKEN_PRICE_USD
├── models/
│   ├── story.py                                 # NEW: Story, CharacterType, CompletionCriteria dataclasses
│   └── story_draft.py                           # NEW: StoryDraft, StoryCreationExchange dataclasses
├── services/
│   ├── llm_service.py                           # NEW: azure-ai-inference client, exchange + generation
│   │                                             #   calls, OpenTelemetry span instrumentation
│   ├── story_draft_service.py                   # NEW: draft CRUD, completeness check, orchestrates
│   │                                             #   llm_service for exchange merge + generation trigger
│   ├── story_service.py                         # NEW: persist/fetch/list Story documents
│   └── cosmos_service.py                        # unchanged
├── api/
│   └── admin/
│       ├── middleware.py                        # unchanged
│       └── stories.py                           # MODIFY: replace create_story/list_stories placeholders
│                                                 #   with create_draft, get_draft, patch_draft,
│                                                 #   post_message, list_stories, get_story
├── function_app.py                              # MODIFY: register new draft/story routes
└── tests/
    ├── unit/
    │   ├── test_llm_service.py                  # NEW
    │   ├── test_story_draft_service.py          # NEW
    │   ├── test_story_service.py                # NEW
    │   └── test_models.py                       # MODIFY: Story/StoryDraft/CharacterType/CompletionCriteria
    └── integration/
        └── test_admin_stories_endpoint.py       # NEW: full draft→generation lifecycle, abandonment/TTL,
                                                  #   malformed-output rejection, single-character-type case

frontend/
├── src/
│   ├── pages/
│   │   ├── AdminPage.jsx                        # MODIFY: link to the new story wizard
│   │   └── AdminStoryWizardPage.jsx             # NEW: wizard shell, step tabs, draft state
│   ├── components/
│   │   └── Admin/
│   │       └── StoryWizard/
│   │           ├── StepNameCover.jsx            # NEW
│   │           ├── StepWorldSetting.jsx         # NEW: world prompt, rules, ConversationPanel,
│   │           │                                #   CharacterTypeList, CompletionCriteriaFields
│   │           ├── StepToneReadingLevel.jsx     # NEW
│   │           ├── StepSessionLength.jsx        # NEW
│   │           ├── ConversationPanel.jsx        # NEW: guiding-question chat UI
│   │           ├── CharacterTypeList.jsx        # NEW: repeatable add/remove rows
│   │           └── CompletionCriteriaFields.jsx # NEW
│   └── services/
│       └── storyDraftService.js                 # NEW: calls /api/admin/stories/drafts* endpoints
└── tests/
    ├── components/
    │   └── StoryWizard/
    │       ├── ConversationPanel.test.jsx       # NEW
    │       ├── CharacterTypeList.test.jsx       # NEW
    │       └── CompletionCriteriaFields.test.jsx # NEW
    └── integration/
        └── admin_story_creation_flow.test.jsx   # NEW
```

## Post-Design Constitution Check

*Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md).*

No new violations surfaced during design. Two items worth confirming explicitly now that the schema and contracts are concrete:

- **Principle VI (Observability)**: contracts/api.md's generation failure path (`502 generation_failed`) still passes through `llm_service.py`'s span instrumentation before the error is returned — a failed generation call is exactly the kind of cost/latency event Principle VI exists to make visible, so it is not skipped on the failure branch. Still ✓ MET.
- **Principle IV (YAGNI)**: data-model.md's `Story` deliberately carries `name`/`coverImageUrl`/`tone`/`readingLevel`/`sessionLengthMinutes`/`chapters` as plain optional fields rather than a formally validated sub-schema, matching the spec's explicit Clarifications decision to defer naming them as Key Entity attributes — building stricter validation for fields the spec hasn't formalized yet would be premature. Still ✓ MET.

Constitution Check gate: **PASS**. Proceed to `/speckit-tasks`.
