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

**Purpose**: Constitution Principle XI (NON-NEGOTIABLE at the time) required the screen design to be explicitly agreed with the requesting user/product owner before any implementation task began. This feature adds user-facing UI (`StepPublish.jsx` and its unpublish confirmation dialog), so the gate applied.

**Superseded 2026-09-06**: the constitution was relaxed to v2.0.0 — Principle XI is now "Implementer Design Latitude (Non-Blocking)", and a pre-implementation design sign-off is no longer required and MUST NOT block implementation. T000 is retained as completed history; it does **not** gate Phase 5, whose UI work proceeds directly under Principle VIII's still-binding design-system and accessibility requirements.

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

**Goal**: An administrator can publish an unpublished story (subject to the FR-008 test-play gate) and unpublish a published one, from either the wizard's new "Publish & assign" step or the administrator story list — both calling the same two backend endpoints. (The list entry point is delivered by Phase 5, added 2026-09-06; Phase 3 itself covers the wizard entry point and the endpoints both callers share.)

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
- [X] T017 Walk through quickstart.md Scenarios 1-3 and 5 manually against a local run (Scenario 4 depends on `008-core-gameplay`/`009-save-and-continue` and is out of scope until those exist — note this explicitly rather than skipping silently); confirm SC-001, SC-002, and SC-004 hold.
  - **Note (2026-09-05, product owner session)**: Scenario 1 (publish blocked without test-play, 409 + FR-011 explanatory text) was confirmed live against the deployed environment (`calm-bay-063862603.7.azurestaticapps.net` / `llmdungeon-func-prod`) via the wizard's real `StepPublish` UI. Scenarios 2, 3, and 5's live re-validation was blocked by environment friction unrelated to the feature itself: no story-list UI yet to return to an already-generated story (`012-story-editing-and-review`'s known, tracked gap — see Notes below), no Cosmos Data Explorer access from the product owner's network (private endpoint), and CORS/token issues when attempting to call the API manually from the browser console outside the app's own request path. The product owner explicitly directed skipping the remainder of manual validation rather than continuing to work around these; automated coverage (`test_admin_stories_publish_endpoint.py`, `test_story_service.py`, `admin_story_publish_flow.test.jsx`) stands in for Scenarios 2/3/5's exact request/response and UI behavior in lieu of a full live walkthrough.
- [X] T018 Final acceptance: request the user/product owner verify the publish/unpublish flow (wizard's "Publish & assign" step) against the deployed or locally running environment, per Constitution Principle IX as it then stood — do not mark this feature done without that explicit sign-off. (**Superseded 2026-09-06**: constitution v2.0.0 makes Principle IX post-ship and non-blocking; this task was satisfied on 2026-09-05 regardless, and Phase 5 requires no equivalent sign-off task.)
  - **Sign-off (2026-09-05)**: Product owner (Reza Mahmood) explicitly directed marking all remaining tasks done after confirming Scenario 1 live and directing that further manual validation be skipped. Treated as final acceptance per Constitution Principle IX.

---

## Dependencies & Execution Order

### Phase Dependencies

- **UI Design Agreement (Phase 0)**: No dependencies — can start immediately. Blocked T007–T014 (all Phase 3 implementation tasks) under Principle XI as it then stood. **Superseded 2026-09-06** (constitution v2.0.0, Principle XI now non-blocking): this phase is completed history and gates nothing further — it does not block Phase 5.
- **Setup (Phase 1)**: No dependencies — can start immediately, in parallel with Phase 0.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all of Phase 3.
- **User Story 1 (Phase 3)**: Depends on Foundational completion and, for T007–T014, on Phase 0's sign-off as the design gate then stood. Test tasks T005/T006 do not touch UI and may start before sign-off. The only story in this feature, so nothing runs in parallel with it at the story level; Phase 5 extends the same story with its second entry point rather than adding a new one.
- **Polish (Phase 4)**: Depends on Phase 3 completion.
- **Convergence (Phase 5)**: Added 2026-09-06 for FR-010's story-list entry point. Depends on Phase 3 being complete — specifically T009 (routes live) and T011 (`publishStory`/`unpublishStory` in `storyDraftService.js`), both already done — and on Phase 4 having landed the `lastPublishedAt` field in the list response (T015, done). Requires **no** backend, contract, or data-model change, and re-opens no earlier task. Phase 0's design gate does not apply to it (constitution v2.0.0, Principle XI non-blocking).

### Within Phase 3

- Tests (T005, T006) should be written and failing before implementation (T007-T012).
- T007 (service layer) before T008 (API handlers) before T009 (route registration).
- T009 (backend routes live) before T011 (frontend service calls them) before T010/T012 (UI wiring) — T010 can be built in parallel with T007-T009 since it only needs the endpoint *contract*, not the live route, but T011 needs T009 merged to be end-to-end testable.
- T013, T014 (frontend tests) depend on T010-T012 being in place.

### Within Phase 5

- T019 (the per-row action itself) is the foundation — T020, T021, and T022 all extend the control it adds and MUST follow it.
- T020, T021, T022 are independent of one another and may be done in any order (or together) once T019 lands, but all three touch `src/frontend/src/pages/AdminPage.jsx`, so they are **not** marked `[P]` — sequence them rather than running them concurrently.
- T023 (tests) is written last in this phase, after T019–T022, so it asserts the finished behavior; it is the only Phase 5 task in a different file, hence the only one eligible for `[P]`.
- T024 (stale comment in `AdminPage.jsx`) has no functional dependency and is naturally folded into T019's edit of that same file; if done separately, do not run it concurrently with T019–T022.

### Parallel Opportunities

- T004 can run in parallel with nothing else in Phase 2 (it's the only non-blocking task after T002/T003, which are sequential edits to the same file).
- T005 and T006 (backend tests, different files) can be written in parallel.
- T013 and T014 (frontend tests, different files) can run in parallel once T012 lands.
- T015 (Polish) can start as soon as T007 lands, in parallel with later Phase 3 frontend tasks.
- Phase 5 offers little parallelism: T019-T022 and T024 all edit `src/frontend/src/pages/AdminPage.jsx` and must be sequenced; only T023 (a separate test file) can run alongside, once T019-T022 are in place.

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

This feature has a single P1 user story — there is no smaller MVP slice within it. Complete Setup → Foundational → User Story 1 → Polish → Convergence, in order. (T018's acceptance sign-off closed Phases 1–4 on 2026-09-05; Phase 5 needs no equivalent gate — constitution v2.0.0 makes Principle IX post-ship and non-blocking.)

### Incremental Delivery

1. Phase 1 + Phase 2: `Story` model carries the three new fields.
2. Phase 3: publish/unpublish is fully usable from the wizard, gate-enforced, idempotent, with FR-011/FR-013 UX in place — this alone satisfies the spec's Independent Test.
3. Phase 4: response-shape completeness, full-suite validation, and sign-off.
4. Phase 5: the same publish/unpublish becomes reachable from the administrator story list (FR-010), completing the spec's second entry point — frontend-only, reusing the endpoints and actions Phase 3 already shipped.

---

## Notes

- **Revised 2026-09-06**: FR-010's story-list entry point is now **in scope for this feature**, delivered by Phase 5 (T019–T024). It was originally deferred to `012-story-editing-and-review` (plan.md, research.md §5) on the assumption that no story list existed yet; in fact the administrator story list already exists at `src/frontend/src/pages/AdminPage.jsx`, so Phase 5 adds the per-row publish/unpublish action to it rather than building a placeholder screen. `012` extends that same list — it does not introduce a second story list or a second publish path.
- `017-story-publish-test-play-gate` owns writing `lastTestPlayedAt`; until it ships, every publish attempt is correctly blocked (T005/T006 assert this as expected behavior, not a bug).
- **Known, tracked coverage gap (FR-005, FR-007, SC-003)**: FR-007 requires an automated test for every distinct publishing outcome, including "unpublish with active sessions in progress." No such automated test exists in this task list — it cannot be written until `008-core-gameplay`/`009-save-and-continue` exist to create an active session. T017 covers it only as a manual quickstart walkthrough (Scenario 4) in the interim. This is a deliberate, explicitly-tracked deferral, not a silent gap: a follow-up task to add the automated test MUST be filed against (or added to) `008`/`009` once they land, before this feature can be considered to fully satisfy FR-007.
- `[P]` tasks touch different files with no unresolved dependency between them.
- Commit after each task or logical group; stop at the Phase 3 checkpoint to validate the story independently before moving to Polish.

---

## Phase 5: Convergence

**Purpose**: Close the gap opened by the 2026-09-06 clarification session, which moved FR-010's story-list entry point into this feature's scope (it was previously deferred to `012-story-editing-and-review`). The backend, endpoints and `storyDraftService` actions all already exist and are unchanged by this phase — the remaining work is entirely in the existing admin story list UI at `src/frontend/src/pages/AdminPage.jsx` and its tests.

- [X] T019 [US1] Add a per-row publish/unpublish action to the existing admin story list in `src/frontend/src/pages/AdminPage.jsx`: give the table a third column whose cell renders a "Publish" button for an unpublished story and an "Unpublish" button for a published one, calling the existing `publishStory`/`unpublishStory` from `src/frontend/src/services/storyDraftService.js` with a token acquired the same way `refresh` already does (`instance.acquireTokenSilent`). Each button MUST act on exactly one story — no multi-select, no bulk control (FR-014) — and MUST stay inside the design-token layer (`.btn`/`.btn-secondary`, existing spacing tokens; Constitution Principle VIII). Share the publish/unpublish call + 409/confirmation handling with `src/frontend/src/components/Admin/StoryWizard/StepPublish.jsx` (extract a small hook or helper both use) rather than duplicating it, so the wizard and the list remain a single publish path (depends on T009/T011 — both already complete; no backend change needed) per FR-010, FR-014, US1/AC4, SC-005 (missing)
- [X] T020 [US1] Require a client-side confirmation before unpublishing from the story list: clicking a row's "Unpublish" opens the same `.dialog`/`.dialog-backdrop` confirmation used in `StepPublish.jsx` (naming the story being unpublished), and `unpublishStory` is only called after the administrator confirms; canceling leaves the row untouched. Publish from a row MUST remain a single direct action with no confirmation (depends on T019) per FR-013 (missing)
- [X] T021 [US1] Handle a gate-blocked publish from the story list: when `publishStory` rejects with a 409, render the response's explanatory message in/next to that story's row (`role="alert"`, design-token text styles) instead of leaving the click silent or the button unexplained-disabled; the row's published status MUST NOT change. Do not add an always-visible readiness indicator to the list — the post-attempt explanation is the whole requirement (depends on T019) per FR-011 (missing)
- [X] T022 [US1] On a successful publish or unpublish from the list, update that one story's row in place from the response's `story` object (its new `published` status, and `lastPublishedAt` if the row shows it) by replacing that entry in `AdminPage.jsx`'s `stories` state — MUST NOT call `refresh()`/reload the whole list, and MUST NOT surface a staleness or conflict error if the returned state differs from what the row was showing; the returned state simply wins (depends on T019, and on T020 for the unpublish path) per FR-016, FR-015 (missing)
- [X] T023 [P] [US1] Extend `src/frontend/tests/integration/admin_stories_list.test.jsx` (or add a sibling `admin_stories_list_publish.test.jsx`) with list-side publishing coverage against a mocked API: publishing an unpublished row calls `publishStory` and flips that row to "Published" without refetching the list; a 409 shows the explanatory text and leaves the row unchanged; unpublishing opens the confirmation and does not call `unpublishStory` until confirmed; canceling the confirmation changes nothing; a redundant publish succeeds idempotently; and only the acted-on row changes when several stories are listed (depends on T019–T022) per FR-007 (missing)
- [X] T024 Correct the stale scope comment in `src/frontend/src/pages/AdminPage.jsx` (the docstring stating "Editing, publishing and deleting stories are deliberately not here; those belong to 005-story-publishing / 012-story-editing-and-review") — publishing now belongs on this screen per FR-010; leave the editing/deleting deferrals to `012` intact (no dependency — may run any time, same file as T019 so do not run it concurrently with T019) per FR-010 (contradicts)

**Checkpoint**: An administrator can publish or unpublish any story directly from the story list in a single row action (with confirmation for unpublish), gated identically to the wizard, with the row reflecting the result in place.

### Out of scope for this phase

- `012-story-editing-and-review`'s own capabilities — editing, the full-configuration view, download and re-upload — remain `012`'s scope; Phase 5 adds only the publish/unpublish action to the list `012` will later extend.
- `017-story-publish-test-play-gate`'s writing of `lastTestPlayedAt` remains `017`'s scope; until it ships, publish attempts from the list are correctly blocked with FR-011 text, exactly as they are from the wizard.
- No backend, endpoint, contract, or data-model change: FR-015 is already satisfied server-side (`story_service.publish`/`unpublish` re-read the story and evaluate the FR-008 gate against stored state), and `list_summaries` already returns `published` and `lastPublishedAt`.
