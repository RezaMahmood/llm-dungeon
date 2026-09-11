# Quickstart: Validate Story and Session Token Usage Tracking

**Date**: 2026-09-11

**Feature**: Story and Session Token Usage Tracking (026-token-usage)

Step-by-step scenarios confirming the stories-list token column, the
published-date hover, and the new Sessions page all work end-to-end. See
[contracts/api.md](contracts/api.md) for exact request/response shapes and
[data-model.md](data-model.md) for the underlying fields.

---

## Prerequisites

1. `004-story-creation-done`, `005-story-publishing-done`,
   `008-core-gameplay-done`, `010-story-test-play` implemented: a story can
   be created, published, played by a player, and test-played by an admin.
2. Backend running with the extended `GET /api/manage/stories` response and
   the new `GET /api/manage/sessions` endpoint.
3. A signed-in Administrator account and at least one signed-in Player
   account.

---

## Scenario 1: A Newly Created Story Shows a Non-Zero Token Total

**Steps**:
1. Create a new story through the admin wizard (world-prompt suggestion,
   then generate).
2. Open the admin stories list.

**Expected**: The story's row shows a `Tokens` column with a positive
number reflecting the world-prompt suggestion plus the generation and
starting-point calls made while creating it. SC-001 satisfied.

---

## Scenario 2: Editing and Test-Playing a Story Increases Its Total

**Steps**:
1. Note a story's current token total from the stories list.
2. Edit the story in a way that triggers content regeneration, and save.
3. Test-play the story for a couple of exchanges.
4. Reload the stories list.

**Expected**: The story's token total is now greater than the value noted
in step 1, reflecting both the edit's regeneration and the test-play
exchanges. SC-003 satisfied.

---

## Scenario 3: A Pre-Existing Story Shows Zero, Not an Error

**Steps**:
1. Identify (or seed) a story persisted before this feature shipped, or a
   story that was created purely by configuration-file import with every
   authored field supplied (no LLM call made).
2. Open the admin stories list.

**Expected**: That story's row shows `0` in the Tokens column — never a
blank cell or an error. FR-004 satisfied.

---

## Scenario 4: The Last-Published Date Moves to a Hover

**Steps**:
1. Publish a story.
2. Open the admin stories list and look at that story's Status cell without
   hovering.
3. Hover the mouse over the "Published" text.

**Expected**: Step 2 shows no visible date text — only the Published tag.
Step 3 reveals the last-published date. An unpublished story's status
indicator shows no date on hover and produces no error. SC-002 satisfied.

---

## Scenario 5: A Player Session Appears on the Sessions Page, Not in the Story Total

**Steps**:
1. Note a published story's token total from the stories list.
2. As a Player, start the story and play a few turns.
3. Reload the stories list, then open the new Sessions page from the admin
   navigation menu.

**Expected**: The story's token total in step 3 is unchanged from step 1
(FR-011). The Sessions page shows a new row for the player's session with
the story's name, a session identifier, a non-zero token total, and the
player's email address. SC-005 satisfied.

---

## Scenario 6: A Test-Play Session Appears on the Sessions Page With the Tester's Email

**Steps**:
1. As an Administrator, test-play a story for a couple of exchanges.
2. Open the Sessions page.

**Expected**: A row appears for the test session showing the story's name,
a session identifier, a non-zero token total, and the *administrator's*
email address (research.md Decision — the tester's own email, not a
placeholder). Acceptance Scenario 2 (User Story 4) satisfied.

---

## Scenario 7: The Sessions Page Is Read-Only and Reachable From Navigation

**Steps**:
1. As an Administrator, look at the admin navigation menu.
2. Click through to the Sessions page.
3. Attempt to find any control that edits, deletes, or otherwise modifies a
   session from that page.

**Expected**: "Sessions" appears as its own menu item alongside Stories,
New story, and People (FR-017). No edit/delete control exists anywhere on
the page (FR-016).

---

## Scenario 8: A Fresh Session Shows Zero Tokens, Not a Blank Row

**Steps**:
1. As a Player, start a new session but do not submit a turn yet (or check
   immediately after creation, before the first interaction completes).
2. Open the Sessions page.

**Expected**: The row for that session shows `0` in its token total —
never a blank cell or an omitted row. FR-018 satisfied.
