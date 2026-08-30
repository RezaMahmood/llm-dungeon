# Quickstart: Validate Story Publishing

**Date**: 2026-08-30

**Feature**: Story Publishing (005-story-publishing)

This guide provides step-by-step validation scenarios confirming story publishing works end-to-end. See [contracts/api.md](contracts/api.md) for exact request/response shapes and [data-model.md](data-model.md) for the extended `Story` schema.

---

## Prerequisites

1. `004-story-creation-done` implemented and deployed (or running locally): a `Story` document can be created via its wizard/API, defaulting to `published: false`.
2. Backend deployed (or running locally) with `POST /api/manage/stories/{storyId}/publish` and `POST /api/manage/stories/{storyId}/unpublish`.
3. A signed-in Administrator account (per `002-login-and-access-control` / `003-account-provisioning`).
4. Until `017-story-publish-test-play-gate` ships, every story has `lastTestPlayedAt: null`, so Scenario 1 below will always return `409` — this is expected (research.md §1). Scenarios that need a passing gate note a manual Cosmos field edit as a stand-in for `017`.

---

## Scenario 1: Publish Is Blocked Without a Qualifying Test Play (FR-008, FR-011)

**Objective**: A newly created story cannot be published until it has a qualifying test play.

**Steps**:
1. Create a story via `004`'s wizard (or `POST /api/manage/stories/drafts` → complete → generated), confirm `published: false`.
2. `POST /api/manage/stories/{storyId}/publish`.

**Expected**: `409 test_play_required` with explanatory text (FR-011); `published` remains `false`. Corresponds to spec.md's Edge Cases (never-test-played story) and SC-004.

---

## Scenario 2: Publish Succeeds Once the Gate Is Satisfied (Acceptance Scenarios 1–2, SC-001, SC-002)

**Objective**: Once test-play is satisfied, publishing makes the story available to players with no other content change.

**Steps**:
1. From Scenario 1's story, set `lastTestPlayedAt` to a timestamp at or after `contentUpdatedAt` (in production this is `017`'s future write path; for local validation before `017` ships, this may require a direct Cosmos field edit as a stand-in).
2. `POST /api/manage/stories/{storyId}/publish`.
3. `GET /api/manage/stories/{storyId}` and confirm `published: true`, `lastPublishedAt` is a recent timestamp, and no other field changed.
4. Confirm the story now appears in the player-facing adventure list (`006-adventure-and-character-setup`) and did not before step 2.

**Expected**: `200 OK`; `published: true`; `lastPublishedAt` set; SC-001 and SC-002 satisfied.

---

## Scenario 3: Publish and Unpublish Are Both Idempotent (FR-006, Edge Cases)

**Steps**:
1. Using the published story from Scenario 2, call `POST /api/manage/stories/{storyId}/publish` again.
2. Confirm `200 OK`, `published: true` (unchanged), `lastPublishedAt` re-stamped to a newer timestamp (research.md §2/§3).
3. `POST /api/manage/stories/{storyId}/unpublish`, confirm `200 OK`, `published: false`.
4. Call `POST /api/manage/stories/{storyId}/unpublish` again.

**Expected**: Both redundant calls succeed with no error (FR-006); no duplicate side effects.

---

## Scenario 4: Unpublishing Does Not Affect Sessions Already In Progress (Acceptance Scenario 3, FR-005, SC-003)

**Prerequisites**: `008-core-gameplay` and `009-save-and-continue` implemented (a player can start and hold an active session).

**Steps**:
1. Publish a story (Scenario 2). As a player, start a play session against it.
2. As the Administrator, unpublish the story (client confirms the "are you sure?" prompt per FR-013 — this is a frontend-only step, not a separate API call).
3. Confirm the story no longer appears in the player-facing adventure list for a *new* session.
4. Confirm the player's already-active session from step 1 continues uninterrupted.

**Expected**: New sessions are blocked; the in-progress session is unaffected. SC-003 satisfied.

---

## Scenario 5: Both Entry Points Enforce the Same Gate (FR-010)

**Objective**: The wizard's "Publish & assign" step and (once `012` exists) the story list both call the same endpoints and see identical gate behavior.

**Steps**:
1. Repeat Scenario 1 from the wizard's `StepPublish.jsx` UI — confirm the blocked-explanation text renders (FR-011).
2. Once `012-story-editing-and-review`'s story list exists, repeat from that screen and confirm the same blocked/allowed behavior.

**Expected**: Identical `409`/`200` behavior regardless of caller, since both call the same backend endpoints (contracts/api.md).
