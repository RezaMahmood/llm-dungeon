# Quickstart: Story Test Play

**Feature**: `010-story-test-play` | **Date**: 2026-09-08

Runnable validation for this feature. Details live in [contracts/api.md](./contracts/api.md)
and [data-model.md](./data-model.md); this file is the run guide.

## Prerequisites

- The worktree's devcontainer (`bin/wt 010-story-test-play`), per
  `docs/WORKTREE_CONTAINER_WORKFLOW.md`.
- Python 3.11 (matching `.github/workflows/test.yml`) and the frontend's Node toolchain.
- No Azure resources. Backend tests stub Cosmos with in-module `FakeCosmosService` /
  `FakeContainer` classes and the LLM with `MagicMock(spec=LLMService)`; frontend tests
  mock the service modules with `vi.mock`.

## Automated tests

```bash
# Backend — from the repo root
pytest src/backend/tests/ -v

# Just this feature
pytest src/backend/tests/unit/test_test_play_session_service.py \
       src/backend/tests/integration/test_admin_test_play_endpoint.py -v

# Frontend
cd src/frontend && npm test
```

New test files **(proposed)**, following the existing naming conventions:

| File | Covers |
|---|---|
| `src/backend/tests/unit/test_test_play_session_service.py` | FR-001, FR-002, FR-004, FR-005, FR-009, FR-010 |
| `src/backend/tests/integration/test_admin_test_play_endpoint.py` | Route auth, status codes, `lastTestPlayedAt` write |
| `src/frontend/tests/components/AdminStoryTestPlayPage.test.jsx` | FR-003, FR-005, FR-006 |
| `src/frontend/tests/integration/admin_test_play_flow.test.jsx` | FR-006, FR-007, FR-008 |
| `src/frontend/tests/components/StoryPublishActions.test.jsx` (existing, extended) | Amended `005` FR-013 publish confirmation |

## Scenario 1 — A draft story becomes publishable (FR-001, FR-002, SC-001)

The headline check: before this feature, `can_publish()` was unsatisfiable and no story
could be published at all.

1. Create a story and confirm `POST /api/manage/stories/{storyId}/publish` returns
   `409 test_play_required`.
2. `POST /api/manage/stories/{storyId}/test-play` → `201` with a turn-0 narrative.
   Publish still returns `409` — starting a session is not an exchange
   (`017` Acceptance Scenario 5).
3. `POST /api/manage/test-play-sessions/{sessionId}/interactions` with
   `{"input": "shout hello at the lighthouse"}` → `200` with a narrative response.
4. Publish now returns `200`.

**Expected**: the story is publishable only after step 3, and `Story.lastTestPlayedAt`
is set while `contentUpdatedAt` is unchanged.

## Scenario 2 — Aborting keeps the story publishable (FR-005, FR-010)

1. Run Scenario 1 through step 3.
2. `DELETE /api/manage/test-play-sessions/{sessionId}` → `200 {"status": "deleted"}`.
3. `GET` that session → `404`.
4. Publish → `200`.

**Expected**: the session is gone; the marker survives it. In the UI, selecting restart
shows the warning **before** anything happens; dismissing it leaves the conversation
intact, and confirming deletes the session and lands on
`/admin/stories/:storyId/edit`.

## Scenario 3 — Concluding offers publish and edit (FR-004, FR-006, FR-007, FR-008, SC-003)

1. Use a story whose `completionCriteria.successConditions` is reachable in one turn (the
   `_story` fixture's `"Find the keeper"` shape), with the stubbed LLM returning
   `newlySatisfiedSuccessConditions: [0]`.
2. Submit an instruction → `200` with `status: "concluded"` and
   `completionReason: {"type": "success", "detail": "Find the keeper"}`.
3. In the UI, the conclusion screen states the playthrough concluded and offers Publish
   and Edit.
4. Publish → confirmation dialog → on confirm, the story publishes and the browser lands
   on `/admin` with that story's row showing **Published**.
5. Edit → `/admin/stories/:storyId/edit` with the story loaded.

**Expected**: one action plus one confirmation reaches either destination. A blocked or
failed publish keeps the administrator on the conclusion screen with an explanation
(spec Edge Cases).

## Scenario 4 — Isolation (FR-009, SC-002)

1. As administrator A, start a test-play session; note its `sessionId`.
2. As administrator B, `GET /api/manage/test-play-sessions/{sessionId}` → `403`.
3. As a dual-role account, pass a test-play `sessionId` to
   `GET /api/game/sessions/{sessionId}` → `404`. The document lives in
   `testPlaySessions`, which no `game/*` route reads.
4. `GET /api/game/sessions` (saved games) never lists a test-play session.
5. Test play against a story does not change the administrator's
   `playerContentSafetyStandings` document.

**Expected**: no test-play state is reachable through any player route.

## Scenario 5 — Publish confirmation at every entry point (amended `005` FR-013)

Verify all three render the same control and each now confirms:

1. Story list row (`/admin`) → Publish → dialog → confirm → row updates in place.
2. Wizard terminal screen (`StepPublish`) → Publish → dialog → confirm.
3. Test-play conclusion screen → Publish → dialog → confirm → navigates to `/admin`.

**Expected**: identical confirmation copy and the same `POST .../publish` call from all
three; unpublish confirmation is unchanged.

## Manual check (optional, non-blocking)

Per Principles IX and XI, human verification does not gate completion. If run: create a
story, test-play it to an ending, publish from the conclusion screen, and confirm it
appears in the player adventure list.

## Accessibility check (FR-011 — not deferred)

FR-011 defers visual design only. Verify on the test-play screen:

- Keyboard-only operation end to end, with a visible `:focus-visible` outline.
- The instruction input has a real `<label>`; buttons are real `<button>` elements.
- The restart warning and publish confirmation use `role="dialog"` with `aria-modal="true"`
  and `aria-labelledby`, matching the existing dialogs.
- The narrative region announces new turns (`aria-live="polite"`, as `StoryPane` does).
- The test/draft marking (FR-003) is conveyed as text, not color alone.
- No literal colors, fonts, or spacing values — tokens and design-system classes only.
