---

description: "Task list for Story Creation (004-story-creation)"
---

# Tasks: Story Creation

**Input**: Design documents from `/specs/004-story-creation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included — FR-007 explicitly requires an automated test for each distinct step (eliciting setting/plot, eliciting character types, eliciting completion criteria, generation, persistence, abandonment), and Constitution Principle I (NON-NEGOTIABLE) requires a test for every functionality/edge case before it is considered complete.

**Organization**: This feature has a single user story (US1, P1) per spec.md, so Setup and Foundational phases carry the shared LLM/data-layer infrastructure, and Phase 3 (US1) carries everything needed to deliver and independently test the guided story-creation flow end to end.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[US1]**: Belongs to User Story 1 — required on every Phase 3 task
- Every description includes its exact file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the new dependencies and configuration this feature needs before any code can use them.

- [ ] T001 Add `azure-ai-inference` and `azure-monitor-opentelemetry` to `src/backend/requirements.txt` (research.md §1, §2)
- [ ] T002 [P] Add `STORY_DRAFTS_CONTAINER`, `STORIES_CONTAINER`, `AZURE_AI_FOUNDRY_ENDPOINT`, `LLM_INPUT_TOKEN_PRICE_USD`, `LLM_OUTPUT_TOKEN_PRICE_USD` to `src/backend/config.py`, and matching placeholder entries to `src/backend/.env.example`
- [ ] T003 [P] Initialize `azure-monitor-opentelemetry` (`configure_azure_monitor()`) once at startup in `src/backend/function_app.py` (research.md §2)

**Checkpoint**: Dependencies installable, configuration keys exist, telemetry exporter wired — nothing functional yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The data model and the shared LLM-calling service every part of User Story 1 depends on.

**⚠️ CRITICAL**: No User Story 1 task may begin until this phase is complete.

- [ ] T004 [P] Create `Story`, `CharacterType`, and `CompletionCriteria` dataclasses (with `to_dict`/`from_dict`, and `CompletionCriteria`'s validation: ≥1 success condition, `rule` required only when more than one condition is defined) in `src/backend/models/story.py` (data-model.md Story / Shared Structures)
- [ ] T005 [P] Create `StoryDraft` and `StoryCreationExchange` dataclasses (with `to_dict`/`from_dict`, the Completeness Rule as a method, and TTL refresh on update) in `src/backend/models/story_draft.py` (data-model.md Story Draft)
- [ ] T006 [P] Implement `src/backend/services/llm_service.py`: `azure.ai.inference.ChatCompletionsClient` built with `DefaultAzureCredential`, `generate_exchange_response()` (JSON-mode call returning `assistantMessage` + `fieldUpdates`) and `generate_story_config()` (JSON-mode call returning `narrativeGuidance`), each wrapped in an OpenTelemetry span with `gen_ai.*` attributes (prompt, response, input/output tokens, computed `gen_ai.cost_usd`, `gen_ai.latency_ms`) (research.md §1, §2, §4; depends on T002 config keys)
- [ ] T007 Extend `src/backend/tests/unit/test_models.py` with cases for `Story`, `StoryDraft`, `CharacterType`, `CompletionCriteria` (rejects empty `successConditions`; rejects missing `rule` when >1 condition; accepts a single character type) (depends on T004, T005)
- [ ] T008 Create `src/backend/tests/unit/test_llm_service.py`: mock `ChatCompletionsClient` to assert exchange/generation calls parse valid JSON, reject invalid/malformed JSON without raising past the caller, and that the OpenTelemetry span's expected attribute keys are populated from a mocked `usage` block (depends on T006)

**Checkpoint**: Models and the LLM client are implemented and unit-tested in isolation — User Story 1 work can now begin.

---

## Phase 3: User Story 1 - Administrator Creates a New Story Through Guided Conversation (Priority: P1)

**Goal**: An administrator starts a session in the four-step wizard, describes an idea in plain language, answers guiding questions, fills in character types and completion criteria through dedicated fields, and gets a complete, persisted, unpublished story with no separate save step.

**Independent Test**: Per spec.md — start a creation session from an empty state, answer the guiding questions, and verify a complete story configuration is persisted automatically at the end, with no manual file editing or separate save action required (see quickstart.md Scenario 1).

### Backend

- [ ] T009 [US1] Implement `src/backend/services/story_draft_service.py`: create draft (optionally seeded with an `idea`, calling `llm_service.generate_exchange_response`), get draft, patch draft fields (validating `CharacterType`/`CompletionCriteria` per data-model.md, rejecting the whole write on the first invalid field), append a message (calling `llm_service.generate_exchange_response` and merging `fieldUpdates`), evaluate the Completeness Rule after every write and trigger `llm_service.generate_story_config()` when met, delete the draft on successful generation, and refresh the TTL on every update
- [ ] T010 [US1] Implement `src/backend/services/story_service.py`: persist a `Story` (via `story_draft_service`'s generation trigger) with `published=False`, get one story by id, list story summaries (`id`, `name`, `published`, `createdAt`)
- [ ] T011 [P] [US1] Create `src/backend/tests/unit/test_story_draft_service.py`: Completeness Rule (all three conditions required), field validation rejection (empty `successConditions`, missing `rule` with 2+ conditions), single-character-type acceptance, contradictory-answer overwrite (latest wins), malformed-generation-output leaves the draft intact and returns an error (Edge Cases) (depends on T009)
- [ ] T012 [P] [US1] Create `src/backend/tests/unit/test_story_service.py`: persisted story defaults to `published=False` (FR-006), list returns summaries only, get-by-id returns full config including `narrativeGuidance` (depends on T010)
- [ ] T013 [US1] Rewrite `src/backend/api/admin/stories.py`: replace the `create_story`/`list_stories` placeholders with `create_draft`, `get_draft`, `patch_draft`, `post_message`, `list_stories`, `get_story` handlers per contracts/api.md, each gated by `authorize_admin` (depends on T009, T010)
- [ ] T014 [US1] Register the new routes in `src/backend/function_app.py`: `POST/GET /api/admin/stories/drafts`, `GET/PATCH /api/admin/stories/drafts/{draftId}`, `POST /api/admin/stories/drafts/{draftId}/messages`, `GET /api/admin/stories`, `GET /api/admin/stories/{storyId}`, removing the old placeholder route registrations (depends on T013)
- [ ] T015 [P] [US1] Create `src/backend/tests/integration/test_admin_stories_endpoint.py` covering, per FR-007: eliciting setting/plot via `POST .../messages`, eliciting character types and completion criteria via `PATCH`, automatic generation + persistence on completeness (SC-001, SC-003), abandonment leaving nothing persisted once the draft's TTL expires (SC-002, using a shortened TTL override per research.md §3), a fresh session not resuming an abandoned one, and a `502 generation_failed` response leaving the draft intact when the mocked Foundry generation call returns invalid output (Edge Cases) (depends on T014)

### Frontend

- [ ] T016 [P] [US1] Create `src/frontend/src/services/storyDraftService.js`: axios calls for create/get/patch draft, post message, list stories, get story, matching contracts/api.md's request/response shapes
- [ ] T017 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/ConversationPanel.jsx`: renders `exchanges`, lets the administrator send a plain-language message, shows the system's next guiding question
- [ ] T018 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/CharacterTypeList.jsx`: repeatable add/remove rows for `name` + `description`, using existing design-token form primitives (research.md §5)
- [ ] T019 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/CompletionCriteriaFields.jsx`: optional max-duration input, success/failure condition list rows, and an any/all rule selector shown only when more than one condition is defined
- [ ] T020 [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepWorldSetting.jsx`: world prompt + rules textareas, embedding `ConversationPanel`, `CharacterTypeList`, and `CompletionCriteriaFields` (depends on T017, T018, T019)
- [ ] T021 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepNameCover.jsx`: name and cover-image fields
- [ ] T022 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepToneReadingLevel.jsx`: tone and reading-level fields
- [ ] T023 [P] [US1] Build `src/frontend/src/components/Admin/StoryWizard/StepSessionLength.jsx`: session-length and chapter-count fields
- [ ] T024 [US1] Build `src/frontend/src/pages/AdminStoryWizardPage.jsx`: step-tab shell (reachable in any order, per Clarifications) holding the current draft state, calling `storyDraftService`, and rendering the "generated" result once the wizard reports `status: "generated"` (depends on T016, T020, T021, T022, T023)
- [ ] T025 [US1] Wire a "New story" entry point from `src/frontend/src/pages/AdminPage.jsx` to `AdminStoryWizardPage.jsx` (depends on T024)
- [ ] T026 [P] [US1] Create `src/frontend/tests/components/StoryWizard/ConversationPanel.test.jsx` (depends on T017)
- [ ] T027 [P] [US1] Create `src/frontend/tests/components/StoryWizard/CharacterTypeList.test.jsx` (depends on T018)
- [ ] T028 [P] [US1] Create `src/frontend/tests/components/StoryWizard/CompletionCriteriaFields.test.jsx` (depends on T019)
- [ ] T029 [US1] Create `src/frontend/tests/integration/admin_story_creation_flow.test.jsx`: full flow from opening the wizard through a generated, unpublished story, with `storyDraftService` mocked (depends on T024, T025)

**Checkpoint**: User Story 1 is independently complete and testable — quickstart.md's five scenarios all pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [ ] T030 [P] Update `src/backend/README.md` documenting the new story-creation endpoints and the `AZURE_AI_FOUNDRY_ENDPOINT`/`LLM_*_TOKEN_PRICE_USD` configuration
- [ ] T031 [P] Update `src/frontend/README.md` documenting the new admin story-wizard route
- [ ] T032 Run the full backend (`pytest`) and frontend (`vitest run`) suites and confirm every new and existing test passes

---

## Dependencies

- **Phase 1 (Setup)** has no dependencies — start immediately.
- **Phase 2 (Foundational)** depends on Phase 1 (T006 needs T002's config keys). Blocks Phase 3 entirely.
- **Phase 3 (US1)** depends on Phase 2 (models and `llm_service` must exist first). Backend tasks T009–T015 must precede or accompany the frontend tasks that call them (T016 needs the contract, not the implementation, so it can start once contracts/api.md is stable — already true).
- **Phase 4 (Polish)** depends on Phase 3 being complete.
- Cosmos containers `storyDrafts` (TTL-enabled) and `stories` are provisioned by `007-azure-infrastructure-provisioning`, not by any task here — a prerequisite for integration testing against a real Cosmos instance, not a blocker for unit-tested application code.

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
