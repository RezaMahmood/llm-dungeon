# Implementation Plan: Story Creation

**Branch**: `004-story-creation` | **Date**: 2026-08-29 | **Revised**: 2026-08-31 | **Spec**: `specs/004-story-creation/spec.md`

**Input**: Feature specification from `/specs/004-story-creation/spec.md`

## Revision note (2026-08-31)

This plan was rewritten after the T033 acceptance walkthrough (2026-08-30) surfaced two problems with the originally-implemented auto-generate-on-completeness design (see spec.md's now-resolved "Open Questions" section and research.md §7): the wizard could jump to a finished, generated-story screen before the administrator ever visited every tab, and `coverImageUrl`'s meaning was never actually specified. The Session 2026-08-30 Clarifications resolved both, replacing the design described below with an explicit Save/Abandon/Finished flow. Everything in this plan reflects that redesign; the original auto-generate design (StoryDraft, Cosmos TTL draft container, the multi-turn guiding-question exchange) is removed, not merely deprecated.

## Summary

Give a signed-in Administrator a four-tab wizard (name & cover, world & setting, tone & reading level, session length — reachable in any order, per `specs/designs/04-admin-wizard.html`) for building a `Story`. Nothing is written to the database until the administrator explicitly hits **Save**, available from any tab at any time; the first Save creates the record (name required, everything else optional), later Saves update it. **Abandon** (confirmed) discards any local-storage draft and deletes the Story if one was ever saved, then returns to `/admin`. **Finished** (confirmed) simply ends the session, leaving whatever was saved intact, and also returns to `/admin` (which doubles as the stories list). In-progress, unsaved field values across all four tabs live in the browser's local storage, not on the server. Tab 01's optional cover image is a file uploaded from the administrator's device, written to blob storage on Save. Tab 02 offers a single, one-shot LLM "Suggest" action for the outline — not an ongoing conversation.

**This is still the first feature to make a real LLM call** (Tab 02's outline suggestion) and the first to use blob storage, but both now build on infrastructure `007-azure-infrastructure-provisioning` already provisions generically (an Azure OpenAI resource, and a Storage Account + `assets` container) — no new Terraform resources are needed (research.md §6).

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 18 via Vite (frontend, existing)

**Primary Dependencies**:
- Backend (existing): `azure-functions`, `azure-cosmos`, `azure-identity`, `PyJWT[crypto]`, `python-dotenv`, `requests`, `agent-framework-openai`, `azure-monitor-opentelemetry`
- Backend (new): `azure-storage-blob` — cover image upload via Managed Identity (research.md §6)
- Frontend (existing): React 18, `@azure/msal-react`, `axios`, `react-router-dom`

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — one container, `stories` (persisted, unpublished-by-default). No draft container exists in this design — draft state is browser `localStorage` only (data-model.md, research.md §7). Azure Storage `assets` blob container (also `007`-provisioned) holds cover images under a `story-covers/{storyId}/` prefix (research.md §6).

**Testing**: pytest (backend `src/backend/tests/unit`, `src/backend/tests/integration`, existing convention, with the LLM client and blob client mocked); Vitest + React Testing Library (frontend `src/frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `src/backend/` + `src/frontend/` structure)

**Performance Goals**: N/A — no throughput/latency target specified or needed (Principle IV)

**Constraints**: No resume-after-Abandon capability (Assumptions); no story-count limit; multiple concurrent in-progress sessions per administrator are free (each browser tab/session's local storage is independent, per Assumptions) rather than something the backend needs to manage

**Scale/Scope**: Same small administrator population as `003-account-provisioning-done`; one wizard screen (four tabs) plus a small blob-upload service addition

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-007 enumerates every distinct step needing a test (Save/create, Save/update, cross-tab local-storage persistence, Tab 02 outline suggestion, Abandon, Finished); contracts/api.md and data-model.md give concrete request/response and entity shapes for those tests to assert against.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — Every new endpoint (create/update/delete/cover-image/suggest-outline/list/get) is gated by the existing `authorize_admin` middleware; no anonymous access to story data.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model. `azure-storage-blob` is a library addition within the existing Python/Azure Functions stack, not a stack deviation.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — Removing the server-side draft container, its TTL semantics, and the multi-turn conversational merge logic (research.md §7) is itself a YAGNI correction: that infrastructure existed to support a design this redesign no longer needs. Cover images reuse `007`'s existing generic assets container under a path prefix rather than provisioning a dedicated one (research.md §6). Story/draft listing still has no pagination at this project's stated scale.

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI; no new CI configuration needed.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: ✓ MET — Tab 02's one-shot outline suggestion is the one LLM call this feature keeps; it is wrapped in an OpenTelemetry span (`gen_ai.story_creation.suggest_outline`) carrying the full prompt, full response, input/output token counts, computed USD cost, and latency, exported to Application Insights via `azure-monitor-opentelemetry` (unchanged from the original design's §1/§2 research, just narrowed to one call instead of two).

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — The LLM client and the new `BlobService` both authenticate via `DefaultAzureCredential` (Managed Identity), matching `CosmosService`'s existing pattern; no API key, connection string, or client-supplied blob URL is introduced. Private-endpoint enforcement is `007`'s network-layer responsibility for both the Azure OpenAI resource and the Storage Account; this plan introduces no code path that bypasses it.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET — The wizard shell keeps `specs/designs/04-admin-wizard.html`'s step-tab layout and `src/frontend/src/styles/designTokens.css` tokens/primitives (`.field`, `.input`, `.btn*`, `.dialog*` for the Abandon/Finished confirmations, matching `AccountList.jsx`'s existing confirm-dialog pattern). The cover image preview is rendered in grayscale per the design system's photography rule. Character-type/completion-criteria fields are unchanged repeatable-row lists from the original design (research.md §5).

### Principle IX – User-Verified Acceptance Before Completion (NON-NEGOTIABLE)
**Status**: Pending — T033 was attempted once against the original design and found it non-conformant to spec.md (the trigger for this redesign); it must be re-attempted against the redesigned flow before this feature is considered complete. Not satisfied by this plan or by automated tests alone.

### Security & Access Control Requirements (constitution, non-principle section)
**Status**: ✓ MET — No secrets introduced (LLM and blob auth are both Managed Identity, per Principle VII); story data is only ever reachable by an authenticated, allow-listed Administrator.

No unjustified violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-story-creation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (§6, §7 added 2026-08-31)
├── data-model.md         # Phase 1 output (rewritten 2026-08-31)
├── quickstart.md         # Phase 1 output (rewritten 2026-08-31)
├── contracts/            # Phase 1 output
│   └── api.md            # rewritten 2026-08-31
└── tasks.md              # Phase 2 output (amended 2026-08-31)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout (`src/backend/` Python Azure Functions + `src/frontend/` React SPA). This revision removes the draft model/service layer entirely and adds a small blob-storage service; it does not modify any file `002`/`003` own.

```text
src/backend/
├── config.py                                    # MODIFY: remove STORY_DRAFTS_CONTAINER; add
│                                                 #   STORAGE_ACCOUNT_URL, STORY_COVER_IMAGES_CONTAINER
├── models/
│   ├── story.py                                 # MODIFY: name required (only), coverImageUrl/
│   │                                             #   outline/rules/characterTypes/completionCriteria
│   │                                             #   optional; add createdBy/createdAt/updatedBy/updatedAt
│   └── story_draft.py                           # REMOVED — no more server-side draft entity
├── services/
│   ├── llm_service.py                           # MODIFY: only `suggest_outline()` remains (the
│   │                                             #   multi-turn exchange call is removed)
│   ├── blob_service.py                          # NEW: cover image upload via Managed Identity
│   ├── story_service.py                         # MODIFY: create/update/delete/upload_cover_image/
│   │                                             #   get/list — explicit Save/Abandon semantics
│   ├── story_draft_service.py                   # REMOVED
│   └── cosmos_service.py                        # unchanged
├── api/
│   └── admin/
│       ├── middleware.py                        # unchanged
│       └── stories.py                           # MODIFY: create_story, update_story, delete_story,
│                                                 #   upload_cover_image, suggest_outline, list_stories,
│                                                 #   get_story
├── function_app.py                              # MODIFY: register the new story routes, remove the
│                                                 #   old draft routes
└── tests/
    ├── unit/
    │   ├── test_llm_service.py                  # MODIFY: only suggest_outline
    │   ├── test_blob_service.py                 # NEW
    │   ├── test_story_service.py                # MODIFY: create/update/delete/cover-image
    │   ├── test_story_draft_service.py          # REMOVED
    │   └── test_models.py                       # MODIFY: Story (name-only-required), CharacterType,
    │                                             #   CompletionCriteria; StoryDraft cases removed
    └── integration/
        └── test_admin_stories_endpoint.py       # REWRITTEN: Save create/update, Abandon (incl.
                                                  #   never-saved no-op), cover image upload,
                                                  #   suggest-outline success/failure, listing

src/frontend/
├── src/
│   ├── pages/
│   │   ├── AdminPage.jsx                        # MODIFY: import path only (storyService.js)
│   │   └── AdminStoryWizardPage.jsx             # REWRITTEN: local-storage draft, Save/Abandon/
│   │                                             #   Finished actions, confirm dialogs
│   ├── components/
│   │   └── Admin/
│   │       └── StoryWizard/
│   │           ├── StepNameCover.jsx            # MODIFY: file input + upload-on-Save, no per-step
│   │           │                                #   Save button
│   │           ├── StepWorldSetting.jsx         # MODIFY: outline + rules + Suggest action,
│   │           │                                #   CharacterTypeList, CompletionCriteriaFields
│   │           ├── StepToneReadingLevel.jsx     # MODIFY: bound to central field state, no per-step
│   │           │                                #   Save button
│   │           ├── StepSessionLength.jsx        # MODIFY: same
│   │           ├── ConversationPanel.jsx        # REMOVED — Tab 02 no longer has a multi-turn chat
│   │           ├── CharacterTypeList.jsx        # unchanged
│   │           └── CompletionCriteriaFields.jsx # unchanged
│   └── services/
│       └── storyService.js                      # RENAMED from storyDraftService.js; new function set
│                                                 #   (createStory/updateStory/deleteStory/
│                                                 #   uploadCoverImage/suggestOutline/listStories/getStory)
└── tests/
    ├── components/
    │   └── StoryWizard/
    │       ├── CharacterTypeList.test.jsx       # unchanged
    │       └── CompletionCriteriaFields.test.jsx # unchanged
    │       (ConversationPanel.test.jsx removed)
    └── integration/
        ├── admin_story_wizard_flow.test.jsx     # NEW — replaces admin_story_creation_flow.test.jsx
        │                                         #   and wizard_nav_persistence.test.jsx
        └── admin_stories_list.test.jsx          # MODIFY: import path only
```

## Post-Design Constitution Check

*Re-evaluated after the 2026-08-31 redesign (data-model.md, contracts/, quickstart.md).*

- **Principle VI (Observability)**: `suggest-outline`'s `502 generation_failed` path still passes through `llm_service.py`'s span instrumentation before the error is returned — a failed LLM call remains a cost/latency event Principle VI requires visibility into. Still ✓ MET.
- **Principle IV (YAGNI)**: Removing the draft container/TTL/multi-turn-exchange machinery (research.md §7) is itself the redesign's biggest YAGNI correction — that infrastructure served a design no longer in scope. Still ✓ MET.
- **Principle IX (User-Verified Acceptance)**: Still open — see Constitution Check above. T033 remains unchecked in tasks.md pending a human product-owner re-attempt against this redesigned flow; this plan does not claim to satisfy it.

Constitution Check gate: **PASS** (Principle IX intentionally left as the one open, human-only gate). Proceed to `/speckit-tasks`.
