---

description: "Task list for 005-story-publishing"
---

# Tasks: Story Publishing

**Input**: Design documents from `/specs/005-story-publishing/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: FR-007 explicitly requires an automated test for every distinct publishing outcome — test tasks are included.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

No new setup — this feature extends `004-story-creation`'s already-implemented `Story` model, `story_service.py`, `api/admin/stories.py`, and `function_app.py` routing. No new dependencies.

## Phase 2: Foundational

- [x] T001 Add `lastPublishedAt`, `contentUpdatedAt`, `lastTestPlayedAt` fields to `Story` in `src/backend/models/story.py` (dataclass fields, `to_dict`/`from_dict`); stamp `contentUpdatedAt = createdAt` and `lastPublishedAt = None`/`lastTestPlayedAt = None` at creation in `src/backend/services/story_service.py`'s `create_story`.

**Checkpoint**: `Story` carries the fields the publish gate and endpoints below need.

---

## Phase 3: User Story 1 - Administrator Publishes or Unpublishes a Story (Priority: P1) 🎯 MVP

**Goal**: An administrator can publish a story (subject to the FR-008 test-play gate) and unpublish it, from the wizard's "Publish & assign" step, idempotently, with `lastPublishedAt` retained across unpublish.

**Independent Test**: Create a story, confirm it is unpublished; attempt publish before a qualifying test play (blocked, 409 with explanation); satisfy the gate; publish (200, appears available); unpublish with confirmation (200); repeat both calls to confirm idempotency; confirm `lastPublishedAt` survives the unpublish.

### Tests for User Story 1

- [x] T002 [P] [US1] Unit tests for `StoryService.can_publish`, `publish`, `unpublish` (gate blocked/allowed, idempotent publish/unpublish, `lastPublishedAt` re-stamped on publish and untouched by unpublish, 404 on unknown id) in `src/backend/tests/unit/test_story_service.py`.
- [x] T003 [P] [US1] Integration tests for `POST /api/manage/stories/{storyId}/publish` and `POST /api/manage/stories/{storyId}/unpublish` (200 success shape, 409 `test_play_required` with message, 404 not_found, redundant publish/unpublish succeed, unauthenticated/non-admin rejected) in `src/backend/tests/integration/test_admin_stories_endpoint.py`.
- [x] T004 [P] [US1] Component test for `StepPublish.jsx`: renders blocked-explanation text when gate not satisfied, publish button when satisfied, unpublish confirmation prompt gates the call in `src/frontend/tests/components/StoryWizard/StepPublish.test.jsx`.

### Implementation for User Story 1

- [x] T005 [US1] Add `can_publish(story)`, `publish(story_id)` (raises on gate failure), `unpublish(story_id)` to `StoryService` in `src/backend/services/story_service.py` (depends on T001).
- [x] T006 [US1] Add `publish_story`, `unpublish_story` handlers to `src/backend/api/admin/stories.py` (authorize_admin, 404/409/200 per contracts/api.md) (depends on T005).
- [x] T007 [US1] Register `POST manage/stories/{storyId}/publish` and `POST manage/stories/{storyId}/unpublish` routes in `src/backend/function_app.py` (depends on T006).
- [x] T008 [US1] Add `publishStory(token, storyId)`, `unpublishStory(token, storyId)` to `src/frontend/src/services/storyDraftService.js`.
- [x] T009 [US1] Create `StepPublish.jsx` in `src/frontend/src/components/Admin/StoryWizard/`: publish button, FR-011 blocked-explanation text (from the 409 response body), unpublish button with inline "are you sure?" confirmation (FR-013, client-only) (depends on T008).
- [x] T010 [US1] Wire `StepPublish` as a step in `src/frontend/src/pages/AdminStoryWizardPage.jsx`'s post-generation `story` view (replacing the "Publishing is handled elsewhere" placeholder text) (depends on T009).

**Checkpoint**: User Story 1 fully functional — publish/unpublish reachable from the wizard, gated, idempotent, tested.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T011 Run quickstart.md Scenarios 1-3 manually (or via tests) against the running backend to confirm 200/409/404 shapes match contracts/api.md exactly.

---

## Dependencies & Execution Order

- Phase 2 (T001) blocks all of Phase 3.
- Within Phase 3: T002-T004 (tests) can be written in parallel with each other; T005 depends on T001; T006 depends on T005; T007 depends on T006; T008 is independent of T005-T007 (different codebase side) but needed before T009; T009 depends on T008; T010 depends on T009.
- Phase 4 (T011) depends on all of Phase 3.

## Notes

- No `012-story-editing-and-review` story-list entry point is built here (out of scope per plan.md/research.md §5) — it will call the same two endpoints this feature adds.
- No `017-story-publish-test-play-gate` tracking logic is built here — `lastTestPlayedAt` stays server-computed-null until `017` ships, which is the correct interim state (every publish attempt is blocked, per research.md §1).
