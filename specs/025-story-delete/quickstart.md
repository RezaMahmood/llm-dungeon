# Quickstart: Validate Story Delete

**Date**: 2026-09-07

**Feature**: Story Delete (025-story-delete)

This guide provides step-by-step validation scenarios confirming story deletion — and the related unpublish behavior change it introduces — works end-to-end. See [contracts/api.md](contracts/api.md) for exact request/response shapes and [data-model.md](data-model.md) for the underlying behavior.

---

## Prerequisites

1. `004-story-creation-done` and `005-story-publishing-done` implemented: a `Story` can be created and published/unpublished.
2. `008-core-gameplay-done` and `009-save-and-continue` implemented: a player can start, hold, and list an active `PlaySession`.
3. Backend running with `DELETE /api/manage/stories/{storyId}` and the updated `submit_interaction`/`resume_session`/session-detail/`list_player_sessions` behavior.
4. A signed-in Administrator account and at least one signed-in Player account.

---

## Scenario 1: Delete Removes a Story With No Active Sessions

**Steps**:
1. Create a story (any published state).
2. From the admin story list, choose delete on that row; confirm the destructive-action prompt (FR-002).
3. `GET /api/manage/stories/{storyId}`.

**Expected**: The confirmation prompt's copy explicitly states the action is permanent. After confirming, the story's row disappears from the list without a full reload (FR-012), and step 3 returns `404 not_found` (FR-003, FR-013). SC-001 satisfied.

---

## Scenario 2: Cancelling the Confirmation Leaves the Story Untouched

**Steps**:
1. From the admin story list, choose delete on a story's row.
2. Dismiss/cancel the confirmation prompt instead of confirming.
3. `GET /api/manage/stories/{storyId}`.

**Expected**: No request was sent; step 3 still returns `200 OK` with the story unchanged. SC-004 satisfied.

---

## Scenario 3: Deleting a Published Story Requires No Publish-State Precondition

**Steps**:
1. Publish a story.
2. Delete it via `DELETE /api/manage/stories/{storyId}`.

**Expected**: `200 OK`, `{"status": "deleted", "storyId": "..."}` — deletion is not blocked by, or conditioned on, `published`.

---

## Scenario 4: A Deleted Story's Sessions Are Permanently Removed and Players Are Told "Deleted"

**Steps**:
1. Publish a story. As Player A, start a play session against it and submit at least one turn.
2. As Player B, independently start a *second*, separate session against the same story.
3. As the Administrator, delete the story.
4. `GET` each player's in-progress-games list and confirm neither game appears (FR-010, SC-002).
5. As Player A, submit another turn against their now-removed session id.
6. As Player B, submit a turn against their own (different) session id.

**Expected**: Steps 5 and 6 each return `404 story_deleted` — "Story has been deleted. You can no longer continue this story." — with `promptReturnToList: true` (FR-008, contracts/api.md). Each player is notified independently of the other. SC-002, SC-003 satisfied.

---

## Scenario 5: An Unpublished Story's Sessions Are Preserved, Greyed Out, and Restorable

**Steps**:
1. Publish a story. As a player, start a play session and submit at least one turn.
2. As the Administrator, unpublish the story (client confirms the unpublish "are you sure?" prompt — distinct from delete's, per FR-002).
3. `GET` the player's in-progress-games list.
4. As the player, submit another turn against the same session.
5. As the Administrator, re-publish the story.
6. `GET` the player's in-progress-games list again, then submit another turn.

**Expected**: Step 3 shows the game still present with `available: false` (greyed out), not absent (FR-009). Step 4 returns `409 story_unpublished` — "Story has been unpublished. You can no longer continue this story." — with `promptReturnToList: true`, and the session itself is unchanged (FR-005, FR-007). Step 6 shows `available: true` again and the turn in step 6 succeeds normally, with no separate restore action (FR-011, SC-005).

---

## Scenario 6: A Finished Session Is Unaffected Either Way

**Steps**:
1. Have a player finish a play session against a story (reach a completion condition, `status: 'concluded'`).
2. Delete that story (or, in a separate run, unpublish it).
3. `GET` that player's in-progress-games list, and the session's own detail read.

**Expected**: A concluded session is not removed by delete and is not greyed out by unpublish — its history is unaffected in both cases (Edge Cases).

---

## Scenario 7: Deleting an Already-Deleted Story Reports Not Found, Not a Fresh Success

**Steps**:
1. Delete a story (Scenario 1).
2. `DELETE /api/manage/stories/{storyId}` again against the same id.

**Expected**: `404 not_found` — unlike `publish`/`unpublish`, a repeat delete is not treated as an idempotent success (contracts/api.md Validation Rules).
