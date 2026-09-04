---

description: "Task list for Story Publishing (005-story-publishing)"
---

# Tasks: Story Publishing

**Input**: Design documents from `/specs/005-story-publishing/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: FR-007 explicitly requires an automated test for every distinct publishing outcome, so test tasks are included throughout.

**Organization**: Tasks are grouped by user story. This feature has a single user story (US1 — Administrator Publishes or Unpublishes a Story, P1), so almost all work lives in Phase 3; Setup/Foundational is minimal because `004-story-creation-done`'s `Story` model (`src/backend/models/story.py`), `StoryService` (`src/backend/services/story_service.py`), admin story endpoints (`src/backend/api/admin/stories.py`), and wizard shell already exist in this codebase (verified in `src/backend/` and `src/frontend/` — plan.md's `manage/stories.py` naming refers to the URL prefix, not the file path, which is actually `src/backend/api/admin/stories.py`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 — the only story in this feature)
- Include exact file paths in descriptions

## Path Conventions

Existing web-application layout: `src/backend/` (Python Azure Functions) + `src/frontend/` (React SPA via Vite), per plan.md.

---

## Phase 0: UI Design Agreement

**Purpose**: Constitution Principle XI (NON-NEGOTIABLE) requires the screen design to be explicitly agreed with the requesting user/product owner before any implementation task begins. This feature adds user-facing UI (`StepPublish.jsx` and its unpublish confirmation dialog), so this gate applies.

- [X] T000 **UI design agreement/sign-off** (Constitution Principle XI, NON-NEGOTIABLE): the requesting user or product owner reviews the "Publish & assign" step design at `specs/designs/04-admin-wizard.html` (steps 05–06) and confirms two things as the design for T010–T014's implementation: (1) the blocked/allowed publish UI and the unpublish confirmation dialog (reusing the `.dialog`/`.dialog-backdrop` pattern from `src/frontend/src/components/Admin/AccountList.jsx`, per research.md §4), and (2) that `StepPublish` renders in the wizard's post-generation "story generated" view (since a `Story` does not exist until generation completes, unlike the mockup's "reachable in any order" tab framing — see tasks.md Notes) rather than as a `STEPS`-array tab. This task is not complete until that confirmation is given; the design artifact existing is not sufficient. **Gates all implementation tasks below (T007–T014).**

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the feature's foundation is where the plan expects it before extending it.

- [X] T001 Verify `src/backend/models/story.py`, `src/backend/services/story_service.py`, `src/backend/api/admin/stories.py`, and `src/backend/function_app.py` (the `004-story-creation-done` deliverables this feature extends) are present and match data-model.md's assumed starting shape; note any drift before proceeding (no file changes in this task).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the `Story` model with the three new fields (data-model.md) that every later task in this feature reads or writes. MUST complete before any US1 task.

**⚠️ CRITICAL**: No US1 work can begin until this phase is complete.

- [X] T002 Add `lastPublishedAt: Optional[str] = None`, `contentUpdatedAt: str`, and `lastTestPlayedAt: Optional[str] = None` fields to the `Story` dataclass in `src/backend/models/story.py`, including them in `to_dict()`/`from_dict()` (data-model.md's New/changed properties table); `contentUpdatedAt` has no default since it is always required, matching the dataclass's existing required/optional field ordering.
- [X] T003 In `src/backend/services/story_service.py`'s `create_story`, compute the creation timestamp once (e.g. `created_at = _now()`) and pass that same value to both `createdAt` and `contentUpdatedAt` — calling `_now()` twice would let the two values drift by up to a second, breaking the exact equality data-model.md and T004 require ("Stamped equal to `createdAt` at creation"); leave `lastPublishedAt`/`lastTestPlayedAt` at their `None` defaults.
- [X] T004 [P] Update `test_create_story_defaults_to_unpublished` and add a new assertion in `src/backend/tests/unit/test_story_service.py` confirming a freshly created story has `contentUpdatedAt` exactly equal to `createdAt` (not merely close in time) and `lastPublishedAt`/`lastTestPlayedAt` both `None`.

**Checkpoint**: `Story` model and creation path carry all three new fields — US1 implementation can now begin.

---

## Phase 3: User Story 1 - Administrator Publishes or Unpublishes a Story (Priority: P1) 🎯 MVP

**Goal**: An administrator can publish an unpublished story (subject to the FR-008 test-play gate) and unpublish a published one, from either the wizard's new "Publish & assign" step or (once it exists) the story list — both calling the same two backend endpoints.

**Independent Test**: Create a story, verify it is absent from the player-facing adventure list, publish it (after satisfying the gate), verify it appears; unpublish it and verify it no longer appears for new sessions while any in-progress session is unaffected.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation (FR-007 requires a test per distinct outcome).

- [X] T005 [P] [US1] Unit tests for the FR-008 gate helper and `publish`/`unpublish` service methods in `src/backend/tests/unit/test_story_service.py`: gate blocked when `lastTestPlayedAt` is `None`; gate blocked when `lastTestPlayedAt < contentUpdatedAt`; gate satisfied publish sets `published=True` and re-stamps `lastPublishedAt`; redundant publish (already published, gate satisfied) re-stamps `lastPublishedAt` and returns success; unpublish sets `published=False` and leaves `lastPublishedAt` unchanged; redundant unpublish is a no-op success (research.md §1-§3, data-model.md State Transitions).
- [X] T006 [P] [US1] Integration tests for `POST /api/manage/stories/{storyId}/publish` and `POST /api/manage/stories/{storyId}/unpublish` in `src/backend/tests/integration/test_admin_stories_publish_endpoint.py` (new file, following the `FakeCosmosService`/`_patched_authorize_admin` pattern in `test_admin_stories_endpoint.py`): 404 for a nonexistent story on both endpoints; 409 `test_play_required` with FR-011 explanatory text when the gate is unsatisfied; 200 with `published:true` + fresh `lastPublishedAt` once the gate is satisfied; redundant publish returns 200 idempotently (FR-006); unpublish returns 200 with `published:false` and unchanged `lastPublishedAt`; redundant unpublish returns 200 idempotently; unauthenticated/non-admin requests are rejected on both endpoints (Principle II) — this covers every FR-007 outcome plus SC-004.

### Implementation for User Story 1

- [X] T007 [US1] Add a `can_publish(story) -> bool` gate check and `publish(story_id) -> Story | None` / `unpublish(story_id) -> Story | None` methods to `src/backend/services/story_service.py`: `publish` returns `None` on missing story, raises/returns a sentinel the API layer maps to 409 when the gate fails (`lastTestPlayedAt is None or lastTestPlayedAt < contentUpdatedAt`), otherwise sets `published=True` and `lastPublishedAt=_now()` and persists via `upsert_item`; `unpublish` returns `None` on missing story, otherwise sets `published=False` (leaving `lastPublishedAt` untouched) and persists — both unconditional writes per research.md §3 (depends on T002, T003).
- [X] T008 [US1] Add `publish_story` and `unpublish_story` handlers to `src/backend/api/admin/stories.py`, following the existing `get_story`/`list_stories` pattern (`authorize_admin` guard, `story_id = req.route_params.get("storyId")`, 404 via `error_response(404, "not_found", "Story not found")`); on a gate failure return `error_response(409, "test_play_required", "This story must be test-played since its last content change before it can be published.")` (contracts/api.md); on success return `json_response({"status": "success", "story": story.to_dict()}, status_code=200)` (depends on T007).
- [X] T009 [US1] Register `POST manage/stories/{storyId}/publish` and `POST manage/stories/{storyId}/unpublish` routes in `src/backend/function_app.py`, importing `publish_story`/`unpublish_story` alongside the existing `backend.api.admin.stories` imports and wiring them through the existing `_guarded(...)` wrapper used by `admin_stories_get` (depends on T008).
- [X] T010 [US1] Create `src/frontend/src/components/Admin/StoryWizard/StepPublish.jsx`: shows the story's current `published`/`lastPublishedAt` state; a "Publish" button that calls `publishStory`, and on a 409 response renders the FR-011 explanatory text inline (not a disabled control with no explanation) instead of navigating away; an "Unpublish" button that opens a client-side confirmation dialog (reusing the `.dialog`/`.dialog-backdrop` pattern already used in `src/frontend/src/components/Admin/AccountList.jsx`, per research.md §4 and FR-013) reading "Are you sure? Unpublishing removes this story from every player's adventure list." before calling `unpublishStory`; publish requires no confirmation step (FR-013).
- [X] T011 [US1] Add `publishStory(token, storyId)` and `unpublishStory(token, storyId)` to `src/frontend/src/services/storyDraftService.js`, following the existing `getStory`/`listStories` pattern (`client.post` to `/manage/stories/${storyId}/publish` / `/unpublish` with `authHeaders(token)`), and export them from the file's default export object (depends on T009).
- [X] T012 [US1] Wire `StepPublish` into `src/frontend/src/pages/AdminStoryWizardPage.jsx` as a fifth step tab (after the generated-story view is reached, since publishing requires an already-generated `Story`, not a `StoryDraft`) — add it to the `story` branch (around line 251-263) so the "Story generated" view also renders `StepPublish` with the generated `story`, `token`, and a callback to refresh the displayed `story` after a publish/unpublish response (depends on T010, T011).
- [X] T013 [P] [US1] Component tests for `StepPublish` in `src/frontend/tests/components/StoryWizard/StepPublish.test.jsx`: renders current published state; clicking Publish on a gate-blocked story shows the FR-011 explanatory text and does not flip `published`; clicking Publish on a gate-satisfied story calls `publishStory` and reflects `published:true`; clicking Unpublish opens the confirmation dialog and does not call `unpublishStory` until confirmed; confirming calls `unpublishStory` and reflects `published:false`; canceling the dialog leaves state unchanged (depends on T010).
- [X] T014 [P] [US1] Integration test `src/frontend/tests/integration/admin_story_publish_flow.test.jsx` covering the full flow end-to-end against a mocked API: generate a story → attempt publish (blocked, 409, explanatory text shown) → (simulate gate satisfied) → publish succeeds → unpublish with confirmation → re-publish (idempotent) — mirrors quickstart.md Scenarios 1-3 (depends on T012).

**Checkpoint**: User Story 1 is fully functional and independently testable — an administrator can publish/unpublish a story from the wizard, gated by FR-008, with FR-011 explanatory text and FR-013 confirmation.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Close out the parts of the spec that span both endpoints and both layers, and validate against the full quickstart.

- [X] T015 [P] Update `GET /api/manage/stories` and `GET /api/manage/stories/{storyId}` response shapes: confirm `list_summaries`/`get_story` in `src/backend/services/story_service.py` and their callers in `src/backend/api/admin/stories.py` already surface `lastPublishedAt` via `to_dict()`/the existing summary query — extend `list_summaries`'s SQL projection in `src/backend/services/story_service.py` to include `c.lastPublishedAt` (contracts/api.md's Validation Rules: "responses gain `lastPublishedAt`"), and add/update the corresponding assertion in `src/backend/tests/unit/test_story_service.py`.
- [X] T016 Run the full backend (`pytest`) and frontend (`vitest`) suites and fix any regressions introduced by T002-T015.
- [ ] T017 Walk through quickstart.md Scenarios 1-3 and 5 manually against a local run (Scenario 4 depends on `008-core-gameplay`/`009-save-and-continue` and is out of scope until those exist — note this explicitly rather than skipping silently); confirm SC-001, SC-002, and SC-004 hold.
  - **Note (implementation session)**: This dev container has neither Azure Functions Core Tools nor a Cosmos DB emulator installed, and the wizard's MSAL sign-in requires a real Azure AD tenant — so a genuine `func start` + browser walkthrough isn't possible from here. Scenarios 1-3 and 5's exact request/response shapes and UI behavior are instead covered end-to-end by the automated suite: `test_admin_stories_publish_endpoint.py` (404/409/200/idempotency/auth over HTTP against the real handlers), `test_story_service.py` (gate/publish/unpublish logic), and `admin_story_publish_flow.test.jsx` (the full generate → blocked → publish → unpublish-with-confirmation → re-publish UI flow against a mocked API). This task's actual manual/local-run walkthrough is still owed — do not check it off until someone runs it against a real local or deployed environment.
- [ ] T018 Final acceptance: request the user/product owner verify the publish/unpublish flow (wizard's "Publish & assign" step) against the deployed or locally running environment, per Constitution Principle IX — do not mark this feature done without that explicit sign-off.

---

## Dependencies & Execution Order

### Phase Dependencies

- **UI Design Agreement (Phase 0)**: No dependencies — can start immediately. BLOCKS T007–T014 (all Phase 3 implementation tasks), per Principle XI.
- **Setup (Phase 1)**: No dependencies — can start immediately, in parallel with Phase 0.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all of Phase 3.
- **User Story 1 (Phase 3)**: Depends on Foundational completion and, for T007–T014, on Phase 0's sign-off. Test tasks T005/T006 do not touch UI and may start before sign-off. The only story in this feature, so nothing runs in parallel with it at the story level.
- **Polish (Phase 4)**: Depends on Phase 3 completion.

### Within Phase 3

- Tests (T005, T006) should be written and failing before implementation (T007-T012).
- T007 (service layer) before T008 (API handlers) before T009 (route registration).
- T009 (backend routes live) before T011 (frontend service calls them) before T010/T012 (UI wiring) — T010 can be built in parallel with T007-T009 since it only needs the endpoint *contract*, not the live route, but T011 needs T009 merged to be end-to-end testable.
- T013, T014 (frontend tests) depend on T010-T012 being in place.

### Parallel Opportunities

- T004 can run in parallel with nothing else in Phase 2 (it's the only non-blocking task after T002/T003, which are sequential edits to the same file).
- T005 and T006 (backend tests, different files) can be written in parallel.
- T013 and T014 (frontend tests, different files) can run in parallel once T012 lands.
- T015 (Polish) can start as soon as T007 lands, in parallel with later Phase 3 frontend tasks.

---

## Parallel Example: Phase 3 Tests

```bash
# Launch backend and frontend test-writing together (different files, no shared dependency):
Task: "Unit tests for gate + publish/unpublish in src/backend/tests/unit/test_story_service.py"
Task: "Integration tests for publish/unpublish endpoints in src/backend/tests/integration/test_admin_stories_publish_endpoint.py"
```

---

## Implementation Strategy

### MVP First (and Only) Scope

This feature has a single P1 user story — there is no smaller MVP slice within it. Complete Setup → Foundational → User Story 1 → Polish, in order, then request final acceptance (T018).

### Incremental Delivery

1. Phase 1 + Phase 2: `Story` model carries the three new fields.
2. Phase 3: publish/unpublish is fully usable from the wizard, gate-enforced, idempotent, with FR-011/FR-013 UX in place — this alone satisfies the spec's Independent Test.
3. Phase 4: response-shape completeness, full-suite validation, and sign-off.

---

## Notes

- `012-story-editing-and-review`'s story-list entry point (FR-010's second caller) is explicitly out of scope for this feature's tasks (plan.md, research.md §5) — it will call the same `publish`/`unpublish` endpoints once it exists; no placeholder screen is built here.
- `017-story-publish-test-play-gate` owns writing `lastTestPlayedAt`; until it ships, every publish attempt is correctly blocked (T005/T006 assert this as expected behavior, not a bug).
- **Known, tracked coverage gap (FR-005, FR-007, SC-003)**: FR-007 requires an automated test for every distinct publishing outcome, including "unpublish with active sessions in progress." No such automated test exists in this task list — it cannot be written until `008-core-gameplay`/`009-save-and-continue` exist to create an active session. T017 covers it only as a manual quickstart walkthrough (Scenario 4) in the interim. This is a deliberate, explicitly-tracked deferral, not a silent gap: a follow-up task to add the automated test MUST be filed against (or added to) `008`/`009` once they land, before this feature can be considered to fully satisfy FR-007.
- `[P]` tasks touch different files with no unresolved dependency between them.
- Commit after each task or logical group; stop at the Phase 3 checkpoint to validate the story independently before moving to Polish.
