---

description: "Task list for Story Creation (004-story-creation)"
---

# Tasks: Story Creation

**Input**: Design documents from `/specs/004-story-creation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included — FR-007 explicitly requires an automated test for each distinct step (eliciting setting/plot, eliciting character types, eliciting completion criteria, generation, persistence, abandonment), and Constitution Principle I (NON-NEGOTIABLE) requires a test for every functionality/edge case before it is considered complete.

**Organization**: This feature has a single user story (US1, P1) per spec.md, so Setup and Foundational phases carry the shared LLM/data-layer infrastructure, and Phase 3 (US1) carries everything needed to deliver and independently test the guided story-creation flow end to end.

## Revision note (2026-08-31)

T033's first attempt (2026-08-30) found the design Phases 1–4 below implemented — auto-generation the moment a `StoryDraft` became "complete" — did not conform to spec.md's intent: it could jump the administrator to a finished, generated-story screen before every tab was even visited, and `coverImageUrl`'s meaning was never defined. The Session 2026-08-30 Clarifications (spec.md) resolved both by replacing auto-generation with explicit Save/Abandon/Finished, a purely frontend local-storage draft, and a blob-stored cover image.

**Phases 1–4 below (T001–T032) are kept as the historical record of what was originally built, not deleted, but are SUPERSEDED** — the `StoryDraft` model, `story_draft_service.py`, the Cosmos-TTL draft container, the multi-turn conversational exchange (`ConversationPanel`, `generate_exchange_response`), and the auto-generate-on-completeness behavior they describe have all been removed from the codebase. Phase 0 (T000) remains valid as-is — the UI design sign-off it records still covers the same four-tab wizard shell. **Phase 5, below Phase 4, carries the actual current implementation** (new task IDs, continuing the numbering) and is what the codebase now matches.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[US1]**: Belongs to User Story 1 — required on every Phase 3 task
- Every description includes its exact file path

---

## Phase 0: UI Design Agreement

**Purpose**: Constitution Principle XI (NON-NEGOTIABLE, added v1.7.0) requires the screen design to be explicitly agreed with the requesting user/product owner before implementation begins.

- [X] T000 **UI design agreement/sign-off** (Constitution Principle XI, NON-NEGOTIABLE): the requesting user or product owner reviews the story-creation wizard design at `specs/designs/04-admin-wizard.html` — steps 1–4 (name & cover, world & setting, tone & reading level, session length), reachable in any order — plus the dedicated character-type and completion-criteria fields this spec adds beyond that static mockup (FR-008, research.md §5, since the mockup has no reference markup for them) — and confirms it as the design for T016–T029's implementation. This task is not complete until that confirmation is given; the design artifact existing is not sufficient. **Gates all implementation tasks below (T001–T032).**

  Signed off 2026-08-30 by the requesting user, accepting the implemented wizard (including the rebuilt numbered-step tabs from PR #71 and the per-step Save buttons from PR #76) as sufficient for now.

**Checkpoint**: Design confirmed — implementation tasks may begin.

---

## Phase 1: Setup (Shared Infrastructure) — SUPERSEDED, see Phase 5

*The tasks below (Phases 1–4) describe the original auto-generate-on-completeness design. They are kept checked off as a historical record of what was built and then replaced — not because they still describe current code. See the Revision note above and Phase 5 for what the codebase now implements.*

**Purpose**: Add the new dependencies and configuration this feature needs before any code can use them.

- [X] T001 Add `azure-ai-inference` and `azure-monitor-opentelemetry` to `src/backend/requirements.txt` (research.md §1, §2)
- [X] T002 [P] Add `STORY_DRAFTS_CONTAINER`, `STORIES_CONTAINER`, `AZURE_AI_FOUNDRY_ENDPOINT`, `LLM_INPUT_TOKEN_PRICE_USD`, `LLM_OUTPUT_TOKEN_PRICE_USD` to `src/backend/config.py`, and matching placeholder entries to `src/backend/.env.example`
- [X] T003 [P] Initialize `azure-monitor-opentelemetry` (`configure_azure_monitor()`) once at startup in `src/backend/function_app.py` (research.md §2)

**Checkpoint**: Dependencies installable, configuration keys exist, telemetry exporter wired — nothing functional yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The data model and the shared LLM-calling service every part of User Story 1 depends on.

**⚠️ CRITICAL**: No User Story 1 task may begin until this phase is complete.

- [X] T004 [P] Create `Story`, `CharacterType`, and `CompletionCriteria` dataclasses (with `to_dict`/`from_dict`, and `CompletionCriteria`'s validation: ≥1 success condition, `rule` required only when more than one condition is defined) in `src/backend/models/story.py` (data-model.md Story / Shared Structures)
- [X] T005 [P] Create `StoryDraft` and `StoryCreationExchange` dataclasses (with `to_dict`/`from_dict`, the Completeness Rule as a method, and TTL refresh on update) in `src/backend/models/story_draft.py` (data-model.md Story Draft)
- [X] T006 [P] Implement `src/backend/services/llm_service.py`: `azure.ai.inference.ChatCompletionsClient` built with `DefaultAzureCredential`, `generate_exchange_response()` (JSON-mode call returning `assistantMessage` + `fieldUpdates`) and `generate_story_config()` (JSON-mode call returning `narrativeGuidance`), each wrapped in an OpenTelemetry span with `gen_ai.*` attributes (prompt, response, input/output tokens, computed `gen_ai.cost_usd`, `gen_ai.latency_ms`) (research.md §1, §2, §4; depends on T002 config keys)
- [X] T007 Extend `src/backend/tests/unit/test_models.py` with cases for `Story`, `StoryDraft`, `CharacterType`, `CompletionCriteria` (rejects empty `successConditions`; rejects missing `rule` when >1 condition; accepts a single character type) (depends on T004, T005)
- [X] T008 Create `src/backend/tests/unit/test_llm_service.py`: mock `ChatCompletionsClient` to assert exchange/generation calls parse valid JSON, reject invalid/malformed JSON without raising past the caller, and that the OpenTelemetry span's expected attribute keys are populated from a mocked `usage` block (depends on T006)

**Checkpoint**: Models and the LLM client are implemented and unit-tested in isolation — User Story 1 work can now begin.

---

## Phase 3: User Story 1 - Administrator Creates a New Story Through Guided Conversation (Priority: P1)

**Goal**: An administrator starts a session in the four-step wizard, describes an idea in plain language, answers guiding questions, fills in character types and completion criteria through dedicated fields, and gets a complete, persisted, unpublished story with no separate save step.

**Independent Test**: Per spec.md — start a creation session from an empty state, answer the guiding questions, and verify a complete story configuration is persisted automatically at the end, with no manual file editing or separate save action required (see quickstart.md Scenario 1).

### Backend

- [X] T009 [US1] Implement `src/backend/services/story_draft_service.py`: create draft (optionally seeded with an `idea`, calling `llm_service.generate_exchange_response`), get draft, patch draft fields (validating `CharacterType`/`CompletionCriteria` per data-model.md, rejecting the whole write on the first invalid field), append a message (calling `llm_service.generate_exchange_response` and merging `fieldUpdates`), evaluate the Completeness Rule after every write and trigger `llm_service.generate_story_config()` when met, delete the draft on successful generation, and refresh the TTL on every update
- [X] T010 [US1] Implement `src/backend/services/story_service.py`: persist a `Story` (via `story_draft_service`'s generation trigger) with `published=False`, get one story by id, list story summaries (`id`, `name`, `published`, `createdAt`)
- [X] T011 [P] [US1] Create `src/backend/tests/unit/test_story_draft_service.py`: Completeness Rule (all three conditions required), field validation rejection (empty `successConditions`, missing `rule` with 2+ conditions), single-character-type acceptance, contradictory-answer overwrite (latest wins), malformed-generation-output leaves the draft intact and returns an error (Edge Cases) (depends on T009)
- [X] T012 [P] [US1] Create `src/backend/tests/unit/test_story_service.py`: persisted story defaults to `published=False` (FR-006), list returns summaries only, get-by-id returns full config including `narrativeGuidance` (depends on T010)
- [X] T013 [US1] Rewrite `src/backend/api/manage/stories.py`: replace the `create_story`/`list_stories` placeholders with `create_draft`, `get_draft`, `patch_draft`, `post_message`, `list_stories`, `get_story` handlers per contracts/api.md, each gated by `authorize_admin` (depends on T009, T010)
- [X] T014 [US1] Register the new routes in `src/backend/function_app.py`: `POST/GET /api/manage/stories/drafts`, `GET/PATCH /api/manage/stories/drafts/{draftId}`, `POST /api/manage/stories/drafts/{draftId}/messages`, `GET /api/manage/stories`, `GET /api/manage/stories/{storyId}`, removing the old placeholder route registrations (depends on T013)
- [X] T015 [P] [US1] Create `src/backend/tests/integration/test_admin_stories_endpoint.py` covering, per FR-007: eliciting setting/plot via `POST .../messages`, eliciting character types and completion criteria via `PATCH`, automatic generation + persistence on completeness (SC-001, SC-003), abandonment leaving nothing persisted once the draft's TTL expires (SC-002, using a shortened TTL override per research.md §3), a fresh session not resuming an abandoned one, and a `502 generation_failed` response leaving the draft intact when the mocked Foundry generation call returns invalid output (Edge Cases) (depends on T014)

### Frontend

- [X] T016 [P] [US1] Create `src/frontend/src/services/storyDraftService.js`: axios calls for create/get/patch draft, post message, list stories, get story, matching contracts/api.md's request/response shapes
- [X] T017 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/ConversationPanel.jsx`: renders `exchanges`, lets the administrator send a plain-language message, shows the system's next guiding question
- [X] T018 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/CharacterTypeList.jsx`: repeatable add/remove rows for `name` + `description`, using existing design-token form primitives (research.md §5)
- [X] T019 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/CompletionCriteriaFields.jsx`: optional max-duration input, success/failure condition list rows, and an any/all rule selector shown only when more than one condition is defined
- [X] T020 [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepWorldSetting.jsx`: world prompt + rules textareas, embedding `ConversationPanel`, `CharacterTypeList`, and `CompletionCriteriaFields` (depends on T017, T018, T019)
- [X] T021 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepNameCover.jsx`: name and cover-image fields
- [X] T022 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepToneReadingLevel.jsx`: tone and reading-level fields
- [X] T023 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepSessionLength.jsx`: session-length and chapter-count fields
- [X] T024 [US1] Build `src/frontend/src/pages/AdminStoryWizardPage.jsx`: step-tab shell (reachable in any order, per Clarifications) holding the current draft state, calling `storyDraftService`, and rendering the "generated" result once the wizard reports `status: "generated"` (depends on T016, T020, T021, T022, T023)
- [X] T025 [US1] Wire a "New story" entry point from `src/frontend/src/pages/AdminPage.jsx` to `AdminStoryWizardPage.jsx` (depends on T024)
- [X] T026 [P] [US1] Create `src/frontend/tests/components/StoryWizard/ConversationPanel.test.jsx` (depends on T017)
- [X] T027 [P] [US1] Create `src/frontend/tests/components/StoryWizard/CharacterTypeList.test.jsx` (depends on T018)
- [X] T028 [P] [US1] Create `src/frontend/tests/components/StoryWizard/CompletionCriteriaFields.test.jsx` (depends on T019)
- [X] T029 [US1] Create `src/frontend/tests/integration/admin_story_creation_flow.test.jsx`: full flow from opening the wizard through a generated, unpublished story, with `storyDraftService` mocked (depends on T024, T025)

**Checkpoint**: User Story 1 is independently complete and testable — quickstart.md's five scenarios all pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T030 [P] Update `src/backend/README.md` documenting the new story-creation endpoints and the `AZURE_AI_FOUNDRY_ENDPOINT`/`LLM_*_TOKEN_PRICE_USD` configuration
- [X] T031 [P] Update `src/frontend/README.md` documenting the new admin story-wizard route
- [X] T032 Run the full backend (`pytest`) and frontend (`vitest run`) suites and confirm every new and existing test passes
- [ ] T033 **User-verified acceptance** (Constitution Principle IX, NON-NEGOTIABLE): the requesting user or product owner — not the implementing agent — signs in as an Administrator against the real deployed environment (or the most representative environment available) and manually runs quickstart.md's Scenario 1 end-to-end: open `/admin/stories/new`, describe a story idea in plain language, answer the guiding question(s), add at least one character type and completion criterion through the dedicated fields, and confirm the wizard lands on a generated, unpublished story with no separate save step. This task is not complete until that confirmation is given; a passing T032 test run does not satisfy it.

  **Blocked (2026-08-30)**: attempted by the requesting user; walkthrough surfaced two open issues (see spec.md's now-resolved "Open Questions" section) — `coverImageUrl`'s meaning was undefined, and the wizard auto-generated/persisted the story as soon as World & setting was complete, jumping straight to the generated-story view before tone/reading level (step 03) and session length (step 04) were ever visited. Verification of steps 03/04 did not happen as a result.

  **Ready for re-attempt (2026-08-31)**: both issues are resolved by the Session 2026-08-30 Clarifications and Phase 5 below — the story is now written to the database only on explicit Save (available from every tab, gated on nothing but a name), the cover image is an uploaded file stored in blob storage, and Abandon/Finished give the administrator an explicit, confirmed way to exit. T033 must still be re-attempted by the requesting user/product owner against this redesigned flow before the feature is considered complete (Constitution Principle IX); this cannot be satisfied by the implementing agent's own testing.

---

## Phase 5: Explicit Save/Abandon/Finished Redesign (2026-08-31)

**Purpose**: Replace the superseded auto-generate-on-completeness design (Phases 1–4) with the Session 2026-08-30 Clarifications' explicit Save/Abandon/Finished flow, a frontend-only local-storage draft, and a blob-stored cover image. All tasks below are implemented and tested; T033 (re-attempt) remains the only open item for this feature.

### Backend

- [X] T034 [P] Remove `src/backend/models/story_draft.py`, `src/backend/services/story_draft_service.py`, and their unit test `test_story_draft_service.py` — no server-side draft entity exists in the new design (research.md §7)
- [X] T035 [P] Rewrite `src/backend/models/story.py`: `Story` now requires only `name`; `coverImageUrl`/`outline` (renamed from `worldPrompt`)/`rules`/`characterTypes`/`completionCriteria` are all optional; add `updatedBy`/`updatedAt` alongside existing `createdBy`/`createdAt` (FR-012); remove `narrativeGuidance` (no longer generated) (data-model.md Story)
- [X] T036 [P] Add `src/backend/services/blob_service.py`: `BlobService.upload_cover_image()` via `azure.storage.blob.BlobServiceClient` + `DefaultAzureCredential`, writing under `story-covers/{storyId}/{filename}` in the shared `007`-provisioned `assets` container (research.md §6); add `azure-storage-blob` to `requirements.txt`, `STORAGE_ACCOUNT_URL`/`STORY_COVER_IMAGES_CONTAINER` to `config.py`/`.env.example`, remove `STORY_DRAFTS_CONTAINER`
- [X] T037 [P] Simplify `src/backend/services/llm_service.py`: remove `generate_exchange_response`/`generate_story_config` and the exchange system prompt; add `suggest_outline(idea) -> str` (Tab 02's one-shot call, FR-003), keeping the same OpenTelemetry span instrumentation pattern (depends on T036 only for shared config, otherwise independent)
- [X] T038 Rewrite `src/backend/services/story_service.py`: `create_story` (Save/create, name required), `update_story` (Save/update, stamps `updatedBy`/`updatedAt`), `delete_story` (Abandon, idempotent no-op if never saved), `upload_cover_image` (delegates to `BlobService`, 404s if the story doesn't exist yet), `get_story`, `list_summaries` (depends on T035, T036)
- [X] T039 Rewrite `src/backend/api/admin/stories.py`: `create_story`, `update_story`, `delete_story`, `upload_cover_image`, `suggest_outline`, `list_stories`, `get_story` handlers per contracts/api.md, each gated by `authorize_admin`; `createdBy`/`updatedBy` read from `authenticate_with_email` per request (FR-012), matching `admin/accounts.py`'s existing pattern (depends on T037, T038)
- [X] T040 Register the new routes in `src/backend/function_app.py`: `POST/GET /api/manage/stories`, `GET/PATCH/DELETE /api/manage/stories/{storyId}`, `POST /api/manage/stories/{storyId}/cover-image`, `POST /api/manage/stories/suggest-outline`, removing the old draft route registrations (depends on T039)
- [X] T041 [P] Rewrite `src/backend/tests/unit/test_models.py`'s Story cases (name-only-required, full-configuration acceptance, round-trip) and remove its `StoryDraft`/`StoryCreationExchange` cases (depends on T035)
- [X] T042 [P] Rewrite `src/backend/tests/unit/test_llm_service.py` for `suggest_outline` only (valid/malformed/missing-key/empty-outline JSON, span attribute population) (depends on T037)
- [X] T043 [P] Add `src/backend/tests/unit/test_blob_service.py`: mocked `BlobServiceClient`, asserts the `story-covers/{storyId}/{filename}` path and content-type/default handling (depends on T036)
- [X] T044 [P] Rewrite `src/backend/tests/unit/test_story_service.py`: create requires only a name, update stamps a new `updatedBy`, delete is idempotent, cover-image upload stores the blob URL and 404s pre-Save, listing/get unchanged in shape (depends on T038)
- [X] T045 Rewrite `src/backend/tests/integration/test_admin_stories_endpoint.py`: Save create/update (incl. a different admin's later Save re-stamping `updatedBy`), Abandon (previously-saved and never-saved no-op cases), cover image upload (success and 404-before-save), Suggest outline (success, `502` failure, missing-idea `422`), listing (depends on T040)

### Frontend

- [X] T046 [P] Rename `src/frontend/src/services/storyDraftService.js` to `storyService.js` with the new function set (`createStory`/`updateStory`/`deleteStory`/`uploadCoverImage`/`suggestOutline`/`listStories`/`getStory`) matching contracts/api.md
- [X] T047 [P] Remove `src/frontend/src/components/Admin/StoryWizard/ConversationPanel.jsx` and its test — Tab 02 no longer has a multi-turn chat (FR-003)
- [X] T048 [P] Update `src/frontend/src/components/Admin/StoryWizard/StepNameCover.jsx`: file input for the cover image (held in local component state as a pending `File`, not localStorage, until Save uploads it), grayscale preview of an already-uploaded `coverImageUrl`, no per-step Save button
- [X] T049 [P] Update `src/frontend/src/components/Admin/StoryWizard/StepWorldSetting.jsx`: outline textarea (editable, scrollable) with a "Suggest" action calling the new one-shot endpoint, a separate rules textarea (FR-011), embedding the unchanged `CharacterTypeList`/`CompletionCriteriaFields`
- [X] T050 [P] Update `src/frontend/src/components/Admin/StoryWizard/StepToneReadingLevel.jsx` and `StepSessionLength.jsx`: bind directly to the wizard's central field state, remove their per-step Save buttons (Save is now a single, page-level, from-any-tab action per FR-004)
- [X] T051 Rewrite `src/frontend/src/pages/AdminStoryWizardPage.jsx`: `localStorage`-backed field state across all four tabs (FR-010), a single page-level Save button (create-then-update semantics, plus uploading a pending cover image after the fields Save), Abandon and Finished actions behind confirm dialogs (`.dialog`/`.dialog-backdrop` primitives, matching `AccountList.jsx`'s existing pattern), redirecting to `/admin` on either (depends on T046, T048, T049, T050)
- [X] T052 Update `src/frontend/src/pages/AdminPage.jsx`'s import path for the renamed `storyService.js` (depends on T046)
- [X] T053 [P] Update `src/frontend/tests/integration/admin_stories_list.test.jsx`'s mocked import path only (depends on T046)
- [X] T054 Replace `src/frontend/tests/integration/admin_story_creation_flow.test.jsx` and `wizard_nav_persistence.test.jsx` with `admin_story_wizard_flow.test.jsx`: local-storage draft surviving tab switches and a full reload, Save's create-then-update semantics, a Save with no name being rejected, confirmed/dismissed Abandon (previously-saved and never-saved), confirmed Finished, Suggest success and failure-leaves-outline-untouched (depends on T051)

### Documentation

- [X] T055 [P] Update `src/backend/README.md`: new endpoint table, `STORAGE_ACCOUNT_URL`/`STORY_COVER_IMAGES_CONTAINER` config, removed draft-endpoint documentation
- [X] T056 [P] Update `src/frontend/README.md`: describe the explicit Save/Abandon/Finished flow, local-storage draft, and cover-image/Suggest endpoints, replacing the auto-generate description
- [X] T057 Run the full backend (`pytest`) and frontend (`vitest run`) suites and confirm every new and existing test passes

**Checkpoint**: The redesigned flow is implemented and automated-test-covered end to end. T033 (Phase 4) is the only remaining item, and requires the human product owner.

---

## Dependencies

- **Phase 0 (UI Design Agreement)** has no dependencies — gates every implementation task below (T001–T032), per Principle XI.
- **Phase 1 (Setup)** depends on Phase 0 (T000).
- **Phase 2 (Foundational)** depends on Phase 1 (T006 needs T002's config keys). Blocks Phase 3 entirely.
- **Phase 3 (US1)** depends on Phase 2 (models and `llm_service` must exist first). Backend tasks T009–T015 must precede or accompany the frontend tasks that call them (T016 needs the contract, not the implementation, so it can start once contracts/api.md is stable — already true).
- **Phase 4 (Polish)** depends on Phase 3 being complete.
- Cosmos container `stories` and the Storage Account `assets` blob container are both provisioned by `007-azure-infrastructure-provisioning`, not by any task here — a prerequisite for testing against real Azure resources, not a blocker for unit-tested application code. (The `storyDrafts` container referenced by the superseded Phases 1–4 above was never actually required by Phase 5's redesign and does not need to be provisioned.)
- **Phase 5** supersedes Phases 1–4's application code but depends on Phase 0 (T000) the same way they did — the UI design sign-off still covers the same four-tab wizard shell. Phase 5's backend tasks (T034–T045) should land before or alongside its frontend tasks (T046–T054), same rationale as the original Phase 3.

## Parallel Example (Phase 2)

```
T004 Create Story/CharacterType/CompletionCriteria dataclasses (src/backend/models/story.py)
T005 Create StoryDraft/StoryCreationExchange dataclasses (src/backend/models/story_draft.py)
T006 Implement llm_service.py (src/backend/services/llm_service.py)
```
All three touch different files and have no dependency on each other — run together, then T007/T008 once their respective inputs exist.

## Parallel Example (Phase 3, frontend)

```
T016 storyDraftService.js
T017 ConversationPanel.jsx
T018 CharacterTypeList.jsx
T019 CompletionCriteriaFields.jsx
T021 StepNameCover.jsx
T022 StepToneReadingLevel.jsx
T023 StepSessionLength.jsx
```
Seven independent files — run together; T020, T024, T025 each wait on the specific pieces they assemble.

## Implementation Strategy

**MVP = User Story 1** (this feature has only one story). Suggested delivery order within it: backend draft/generation path first (T009–T015, independently verifiable via the integration test and `curl`/quickstart.md against a running function host), then the frontend wizard (T016–T029) against that working API. Phase 4 polish is not required for the feature to function, only for documentation completeness.
