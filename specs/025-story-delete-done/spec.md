# Feature Specification: Story Delete

**Feature Branch**: `025-story-delete`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "from the stories list in the administrator section, there needs to be the ability to delete a story. on deletion of a story, the configuration should be removed from the database. players who are using the story would be notified on their next turn that the story has been made unavailable. the user experience should be the same as when a story is unpublished except in this case the story is just removed from the database. all other stories that are currently in progress and based on this story configuration should also be removed. as this is a destructive action, the administrator should be prompted to verify that they really want to delete the story instead of unpublishing it"

**Design Reference**: The administrator's story list already exists and already exposes a per-row publish/unpublish action (see `005-story-publishing-done`, `012-story-editing-and-review`); this feature adds a per-row delete action to that same list.

**Amends**: This spec revises `005-story-publishing-done`'s FR-005 — unpublishing a story now also ends a player's ability to continue an in-progress session against it, not just new sessions from starting. `005-story-publishing-done` is annotated to point here as current on that point.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Permanently Deletes a Story (Priority: P1)

An administrator removes a story entirely from the system — not just hides it from players (unpublish), but erases its configuration from the datastore so it no longer exists anywhere in the admin story list or anywhere else.

**Why this priority**: This is the core capability requested — a way to permanently remove obsolete, mistaken, or unwanted story configurations, rather than leaving them around unpublished indefinitely.

**Independent Test**: From the story list, choose delete on a story, confirm the destructive-action prompt, and verify the story record no longer exists in the datastore and no longer appears anywhere in the administrator's story list.

**Acceptance Scenarios**:

1. **Given** an administrator viewing the story list, **When** they choose the delete action on a story's row, **Then** they are shown a confirmation prompt that explicitly states the action is permanent and cannot be undone, distinct from the "are you sure?" prompt shown for unpublish.
2. **Given** the delete confirmation prompt is shown, **When** the administrator confirms, **Then** the story's configuration record is permanently removed from the datastore and its row disappears from the story list without a full list reload.
3. **Given** the delete confirmation prompt is shown, **When** the administrator dismisses or cancels it, **Then** nothing is deleted and the story remains unchanged in the list.
4. **Given** a story that is currently published, **When** an administrator deletes it, **Then** the deletion proceeds the same as for an unpublished story — publish status is not a precondition for deletion.
5. **Given** a story has just been deleted, **When** the administrator or any other administrator looks for it (e.g., by trying to open it for editing via a stale link), **Then** the system treats it as not found, consistent with how a missing story id is already handled elsewhere (see `012-story-editing-and-review`).

---

### User Story 2 - A Player's In-Progress Session Ends Gracefully When Its Story Becomes Unavailable (Priority: P2)

A player who has a game in progress against a story that becomes unavailable — because an administrator deleted it, or unpublished it — is not left with a broken or confusing experience, and is never surprised mid-view: because this is a request/response single-page app with no push channel, nothing interrupts them while they're actively looking at the play surface. Only the next time their browser makes a request for that session — submitting a turn, or loading their list of in-progress games — does the system discover and report what happened.

Delete and unpublish have different consequences, and the player is told which one applies. For a **deleted** story, the persisted session no longer exists at all: the player is told the story has been deleted and they cannot continue, and the game is gone from their list. For an **unpublished** story, the session is untouched and still there: the player is told the story has been unpublished and they cannot continue, and the game remains visible in their list, greyed out — ready to resume automatically if the administrator republishes it later.

**Why this priority**: This depends on User Story 1 existing (a story must be deletable before its half of this behavior can be observed), and protects players from a confusing broken state for either kind of story unavailability. It is a close second in priority because a delete implementation that breaks player sessions ungracefully would be a significant regression in experience.

**Independent Test**: Start a game as a player against a story. Separately verify both halves: (a) have an administrator unpublish it, then submit the next turn and verify a specific "Story has been unpublished" message with a prompt to return to the list, and verify the game still appears in the list, greyed out; (b) with a different session, have an administrator delete the story, submit the next turn, verify a specific "Story has been deleted" message with the same prompt, and verify the game's persisted session and its list entry are both gone.

**Acceptance Scenarios**:

1. **Given** a player has an in-progress play session against a story, **When** an administrator unpublishes or deletes that story, **Then** nothing is pushed to the player and their already-open play surface is not interrupted mid-view — the browser only learns of the change on its next request.
2. **Given** a player's story has since been deleted, **When** the player next submits an action (takes a turn) in that session, **Then** the system finds the persisted session itself is gone, tells the player specifically "Story has been deleted", states they cannot continue, and prompts them to return to their list of in-progress games — rather than a generic or technical error.
3. **Given** a player's story has since been unpublished, **When** the player next submits an action (takes a turn) in that session, **Then** the system finds the session intact but its story unpublished, blocks the turn, tells the player specifically "Story has been unpublished", and prompts them to return to their list of in-progress games — the session itself is not deleted by this.
4. **Given** a player whose story has been deleted, **When** they open their list of in-progress games, **Then** that game's entry is not present, because its persisted session no longer exists.
5. **Given** a player whose story has been unpublished, **When** they open their list of in-progress games (without necessarily having attempted a turn first), **Then** that game's entry is still present, shown greyed out and not continuable.
6. **Given** a player's greyed-out, unpublished-story game, **When** an administrator later re-publishes that story, **Then** the game's entry becomes normal/continuable again the next time the list is loaded, with no separate restore step.
7. **Given** several different players each have their own in-progress session against the same story, **When** an administrator deletes (or unpublishes) that story, **Then** every affected player's session is handled the same way (all deleted for delete; all preserved-but-blocked for unpublish), and every affected player independently sees the correct outcome the next time they act on their own session or list — no other player's session is affected.
8. **Given** a story has no players currently using it, **When** an administrator deletes or unpublishes it, **Then** the action completes with no player-facing effect to observe, since none exists.

---

### Edge Cases

- An administrator deletes a story that has never been published and has no play sessions at all: the deletion completes immediately with no further side effects.
- An administrator deletes a story while another administrator has it open for editing: the next save attempt by that other administrator against the now-missing story is rejected as not found, consistent with the existing "story id matches no existing story" handling (see `012-story-editing-and-review`).
- An administrator deletes a story while they themselves (or another administrator) have an active test-play session against it: the test-play session is not persisted player data (see `010-story-test-play-done`) and simply becomes unusable; no player-facing notification applies since test play is administrator-only.
- A player's game session for a story was already finished (reached a completion condition) before that story was later unpublished or deleted: since it is not "in progress," it is unaffected either way — a deleted story does not remove an already-concluded session's history, and an unpublished story does not grey it out.
- An administrator attempts to delete a story a second time (e.g., a stale row, or a double-click) after it has already been deleted: the system reports it as not found, not as a fresh successful deletion.
- A player has a story's play surface open in one browser tab and their in-progress-games list open in another at the moment an administrator unpublishes or deletes it: neither tab is pushed an update; each reflects the new state only the next time it is loaded or acted upon.
- A player's turn was already in flight (submitted, awaiting a response) at the exact moment their story was deleted: the in-flight request completes as either a normal turn or the "Story has been deleted" outcome depending on which side of the deletion it lands — either is acceptable, since there is no way to guarantee ordering across two independent, concurrent requests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The administrator story list MUST expose a per-row delete action for each story, in addition to the existing per-row publish/unpublish action (see `005-story-publishing-done`).
- **FR-002**: Before a delete request is sent, the system MUST require the administrator to confirm via a client-side prompt that explicitly warns the action is permanent and cannot be undone; this confirmation MUST be visibly distinct from the unpublish confirmation (see `005-story-publishing-done` FR-013), so an administrator cannot mistake one destructive action for the other.
- **FR-003**: On confirmed delete, the system MUST permanently remove the story's configuration record from the datastore; deletion MUST NOT depend on, or be blocked by, the story's current published/unpublished status.
- **FR-004**: On confirmed delete, the system MUST also permanently remove every in-progress play session (and its persisted state, see `009-save-and-continue`) belonging to the deleted story, regardless of which player owns it — this removal is final and irreversible, matching the story's own removal.
- **FR-005**: Unpublishing a story MUST NOT delete, truncate, or otherwise mutate any player's in-progress play session for it — the session and its full history remain saved exactly as they were; unpublishing only prevents that session from being continued (FR-007).
- **FR-006**: Neither a delete's session removal (FR-004) nor an unpublish's continuation-block (FR-005/FR-007) MUST be pushed to an affected player via any background process, scheduled scan, or real-time/async notification. Each MUST be discovered lazily — only when the player's client next makes a request that touches that session (submitting a turn, or loading their list of in-progress games). A player actively viewing an already-open play surface at the moment their story becomes unavailable MUST NOT be interrupted mid-view; their client simply reflects the new state on its next request.
- **FR-007**: When a player submits a turn against a session belonging to a story that has since been unpublished, the system MUST block the turn (without deleting the session), tell the player specifically "Story has been unpublished", state that they cannot continue, and prompt them to return to their list of in-progress games — rather than a generic or technical error.
- **FR-008**: When a player submits a turn against a session that has been removed because its story was deleted (FR-004), the system MUST tell the player specifically "Story has been deleted", state that they cannot continue, and prompt them to return to their list of in-progress games — rather than a generic or technical error.
- **FR-009**: A player's list of in-progress games MUST show a session whose story has been unpublished as present but visually distinguished as unavailable/non-continuable (e.g., greyed out) rather than omitting it, since the session and the story both still exist.
- **FR-010**: A player's list of in-progress games MUST NOT include a session that was removed by a story deletion (FR-004), since neither the session nor the story it belonged to still exist.
- **FR-011**: If a story is re-published after having been unpublished, every player's session against it MUST automatically become continuable and MUST appear normally (not greyed out) in their list again, the next time that state is evaluated (FR-006) — with no separate administrator or player action required to "restore" it, since unpublish never deleted anything (FR-005).
- **FR-012**: After a story delete completes, the story's row MUST be removed from the administrator's story list in place, without requiring a full reload of the list.
- **FR-013**: Any subsequent attempt to reference a deleted story's id (e.g., re-opening it for editing, re-deleting it, or a stale test-play link) MUST be treated as not found, consistent with the existing handling of a missing story id (see `012-story-editing-and-review`).
- **FR-014**: Each distinct outcome (successful delete with no active sessions, successful delete with one or more in-progress sessions permanently removed, unpublish leaving in-progress sessions intact but non-continuable, cancelled delete confirmation leaving the story untouched, delete of an already-deleted story treated as not found, a player's next turn showing the specific "deleted" message after their session was removed, a player's next turn showing the specific "unpublished" message with the session preserved, a player's list correctly showing an absent entry after delete vs. a greyed-out entry after unpublish, a re-published story's session becoming continuable again) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Story Configuration**: The persisted definition of a story (world prompt, character types, completion criteria, published status, etc., per `004-story-creation-done`); this feature adds permanent removal of this record as a new lifecycle action alongside publish/unpublish.
- **Play Session / Saved Game**: A player's in-progress playthrough of a story and its persisted resumable state (see `008-core-gameplay-done`, `009-save-and-continue`). This feature adds two different fates for this record depending on how its story becomes unavailable: **deleted** stories permanently remove every belonging in-progress session (FR-004); **unpublished** stories never mutate it — whether the player can continue, and how the session is shown in their list, is derived fresh from the story's *current* published state each time it is checked (FR-006, FR-009, FR-011), never stored on the session itself.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of confirmed story deletions in testing result in the story's configuration record being permanently absent from the datastore and from the administrator's story list.
- **SC-002**: 100% of in-progress play sessions belonging to a deleted story are permanently removed in testing, regardless of how many distinct players held one; 100% of in-progress play sessions belonging to a merely-unpublished story remain fully intact (no data loss) in testing.
- **SC-003**: 100% of players who submit a turn against a session affected by a deletion or unpublish, in testing, receive the specific, correct reason ("deleted" vs. "unpublished") and a prompt to return to their list, rather than a generic error.
- **SC-004**: 100% of delete attempts in testing require the administrator to pass through a destructive-action confirmation distinct from the unpublish confirmation before anything is removed; cancelling it leaves the story fully intact.
- **SC-005**: 100% of a player's in-progress-games list entries in testing correctly reflect current story state: normal for a published story, greyed out/non-continuable for an unpublished one, absent for a deleted one — including automatically reverting to normal after a re-publish.

## Assumptions

- "Removed from the database" means the story's configuration record is deleted outright, not soft-deleted or merely flagged — distinguishing it from unpublish, which only toggles a visibility flag and keeps the record (see `005-story-publishing-done`).
- "The user experience should be the same as when a story is unpublished" refers to the *shape* of the player-facing interaction (lazy discovery on next request, a specific plain-language reason, a prompt to return to the list) — not to the underlying data outcome: delete permanently removes the session (FR-004), unpublish never does (FR-005).
- "All other stories that are currently in progress and based on this story configuration should also be removed" means exactly that for **delete**: every in-progress play session for that story is permanently removed (FR-004). This phrasing does not apply to unpublish, which never removes anything.
- Only an Administrator capability (see `002-login-and-access-control`) may delete a story; no separate approval workflow exists, consistent with the existing publish/unpublish model.
- Deletion is a per-story action, one at a time via its own row's control, consistent with the existing publish/unpublish action's lack of multi-select/bulk support (see `005-story-publishing-done` FR-014).
- There is no "undo" or trash/recovery mechanism for a deleted story or the play sessions removed with it; an administrator who wants to preserve players' ability to resume later should unpublish instead (which, per FR-005/FR-011, never touches a session and transparently restores continuability on republish) — this feature's confirmation prompt explicitly reminds them of that alternative.
- No new background job, scheduled task, or real-time/push channel is introduced by this feature; the existing request/response endpoints a player already calls (submitting a turn, loading their in-progress-games list) are simply the two points where the current state (session exists? story published?) is checked.
