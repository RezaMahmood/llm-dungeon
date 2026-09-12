# Phase 0 Research: Story Delete

**Feature**: `025-story-delete` | **Date**: 2026-09-07

All unknowns below were resolved by reading the existing implementation this feature extends (`005-story-publishing-done`, `008-core-gameplay-done`, `009-save-and-continue`, `012-story-editing-and-review`) rather than by introducing new technology — Constitution Principle III fixes the stack (Python/Azure Functions backend, ReactJS frontend, Cosmos DB) and Principle IV (YAGNI) rules out anything more elaborate than reusing that stack's existing patterns.

Delete and unpublish have genuinely different data outcomes and must be kept distinct throughout: delete permanently removes the player's session; unpublish never touches it, only blocks continuation. Decisions below reflect that distinction end to end.

## Decision 1 — Hard delete via each container's native `delete_item`

**Decision**: Add `StoryService.delete_story(story_id)` that calls `self._container().delete_item(item=story_id, partition_key=story_id)`, catching `CosmosResourceNotFoundError` to report "already gone" (mirroring `get_story`'s existing not-found handling). No new Cosmos container, no soft-delete flag.

**Rationale**: `account_provisioning_service.py` (`remove_account`) and `story_draft_service.py` (draft cleanup) already call `delete_item` directly on a container client the same way; `StoryService` already uses `get_container()` for `upsert_item`/`read_item`. This is the smallest change consistent with existing conventions, and matches FR-003's "permanently remove."

**Alternatives considered**: A `deleted: true` soft-delete flag (rejected — blurs the explicit delete-vs-unpublish distinction the spec now insists on: unpublish already owns the flag-based model, delete is a genuinely different, permanent operation).

## Decision 2 — Delete cascades a *hard, permanent* removal of every active Play Session for that story

**Decision**: Add `PlaySessionService.delete_active_sessions_for_adventure(adventure_id)`, a cross-partition query `SELECT c.id FROM c WHERE c.adventureId = @adventureId AND c.status = 'active'` (same shape as the existing `list_player_sessions`/`_deactivate_other_active_sessions` queries), followed by one `container.delete_item(item=row["id"], partition_key=row["id"])` per row (partition key is `id` itself, per `_read_item`). Concluded sessions (`status == 'concluded'`) are left untouched — they are history, not "in progress." This removal is unconditional and irreversible, matching the story's own deletion (FR-004).

**Rationale**: FR-004 requires every in-progress session belonging to a deleted story to be *permanently removed* — not merely hidden or blocked. Because the story is gone forever, there is no future state ("re-publish") that could ever make that session meaningful again, so preserving it would only be dead data. This is the one place a hard delete of session data is correct — unlike unpublish (Decision 3), which is reversible by design.

**Alternatives considered**: A lazy-only approach — leave sessions alone and rely solely on the existing `story is None → AdventureNotFoundError` check the next time the player acts — was rejected as the *sole* mechanism, since it would leave the deleted story's game sitting in the player's continue list indefinitely (contradicting FR-010) and leaves genuinely dead data around with no purpose. The lazy check is still needed as a narrow race-condition backstop (a turn already in flight at the exact moment of cascade deletion — see Decision 4) but is not how removal is primarily achieved.

## Decision 3 — Unpublish never touches Play Session data; continuability is computed live

**Decision**: Unpublish's existing implementation (`StoryService.unpublish`) is completely unchanged by this feature — it still only flips `Story.published`. No `PlaySession` field, method, or query is added for unpublish's sake. Instead, every point where a player's session is used to keep playing — submitting a turn, resuming, or loading the in-progress-games list — re-reads the *current* `Story.published` value at that moment and reacts accordingly (Decision 4, 5).

**Rationale**: FR-005 requires unpublish to never mutate a session, and FR-011 requires a re-publish to transparently restore continuability with "no separate restore step." Storing any kind of "blocked" flag on the session itself would need to be written when unpublished and un-written when re-published — extra state that computing live from `Story.published` makes entirely unnecessary. This is the simplest design satisfying both requirements at once (Principle IV).

**Alternatives considered**: Adding a stored `blockedReason`/`isPlayable` field to `PlaySession`, updated by the unpublish/publish actions (rejected — reintroduces exactly the "second copy of the truth that can drift" problem live computation avoids, and would need its own restore-on-republish logic that live computation gets for free).

## Decision 4 — Two distinct exceptions, two distinct player-facing outcomes, checked at every point a player acts on an existing session

**Decision**: In `play_session_service.py`, the existing `_generate_and_persist_turn`'s `story is None → AdventureNotFoundError` check is joined by a new check: `story is not None and not story.published → StoryUnpublishedError`. Both `submit_interaction` and `resume_session` (and `get_session_detail_for_player`, used to rehydrate the play surface) apply the same two checks before proceeding. The API layer (`api/game/sessions.py`) maps:
- `SessionNotFoundError` (the common outcome after a delete's cascade removed the row) **and** `AdventureNotFoundError` (the narrow race where a turn is in flight at the exact moment of cascade deletion, so the session row still exists an instant longer than its story) → `error_response(404, "story_deleted", "Story has been deleted. You can no longer continue this story.")`
- `StoryUnpublishedError` → `error_response(409, "story_unpublished", "Story has been unpublished. You can no longer continue this story.")`

Both responses additionally carry a `promptReturnToList: true` field the frontend uses to render the "return to your story list" call-to-action (FR-007, FR-008).

**Rationale**: Directly satisfies FR-007/FR-008/SC-003's requirement for a *specific, correct reason* ("deleted" vs. "unpublished"), not one shared "unavailable" message. `404` for the deleted case is semantically correct (the resource is gone); `409` for the unpublished case matches this codebase's existing convention for "the resource exists but the action is blocked by its current state" (`session_inactive`, `session_concluded` are both `409` for the same reason). Extending the check to `resume_session`/`get_session_detail_for_player`, not just `submit_interaction`, closes the gap an earlier analysis pass flagged: a player who reloads/resumes before attempting a turn would otherwise see a stale generic error instead of the specific one.

**Alternatives considered**: One shared `story_unavailable` code for both cases — rejected because the reason is a first-class, player-visible fact the application must distinguish, not an implementation detail to hide behind one generic label. Reusing `SessionNotFoundError`'s existing generic "Session not found" wording unchanged — rejected, fails FR-008's explicit specific-reason requirement.

## Decision 5 — The in-progress-games list is augmented with a live-computed availability flag, not filtered by a stored one

**Decision**: `PlaySessionService.list_player_sessions` already batch-resolves each distinct `adventureId`'s name via `_resolve_adventure_name`; this feature extends that same batch resolution to also fetch each story's current `published` flag (a small addition to the existing per-adventure lookup, reusing `StoryService.get_adventure_summary`'s existing `published` field rather than adding a new query shape) and adds an `available: bool` (or equivalently-named) field to each row in the response: `false` when that row's story is unpublished, `true` otherwise. Because Decision 2 already physically removes a deleted story's active sessions, no additional filtering is needed to keep a deleted story's game out of this list — its row simply no longer exists to be returned.

**Rationale**: Directly implements FR-009 (unpublished session shown, greyed out) and FR-010 (deleted session absent) with the least new surface: FR-010 falls out for free from Decision 2's hard delete, and FR-009 only needs one new boolean per list row, computed the same live way as Decision 4's turn-time check — never stored, so a re-publish is reflected on the very next list load (FR-011) with no separate update path.

**Alternatives considered**: A separate "blocked sessions" endpoint or a client-side re-check per row (rejected — both add a second round-trip or a second code path for information the list query can attach for free while it already resolves each row's adventure name).

## Decision 6 — Orchestration lives in the API handler, not inside `StoryService`

**Decision**: `backend/api/admin/stories.py`'s new `delete_story` handler composes `StoryService.delete_story(story_id)` and `PlaySessionService.delete_active_sessions_for_adventure(story_id)` directly, the same way the existing `create_edit_draft` handler already composes `StoryService` and `StoryDraftService`.

**Rationale**: `PlaySessionService` already imports `StoryService` (`from backend.services.story_service import StoryService`, `play_session_service.py`). Having `StoryService` import `PlaySessionService` back would create a circular import; keeping the two-service composition at the API layer (which already has this exact multi-service pattern) avoids that with no new abstraction.

**Alternatives considered**: A shared "story lifecycle" service layered above both (rejected — Principle IV/YAGNI; the existing handler-level composition pattern already solves this with zero new code structure).

## Decision 7 — Frontend: delete control mirrors the publish/unpublish pattern; two distinct play-surface notices; a greyed-out list row

**Decision**:
- Admin side: add `StoryDeleteAction.jsx` + `useDeleteStory.js`, mirroring `StoryPublishActions.jsx`/`usePublishToggle.js`'s `.dialog`/`.dialog-backdrop`/`role="dialog"` pattern, with confirmation copy naming the action as permanent/irreversible and mentioning in-progress player games will be removed (FR-002). `deleteStory(token, storyId)` added to `storyDraftService.js` (`client.delete(...)`).
- Play surface (`PlayPage.jsx`): two new notice branches — `story_deleted` (404) and `story_unpublished` (409) — each rendering its own specific text plus a "Return to your story list" action, alongside the existing `429`/`409 interaction_in_progress`/`409 session_inactive`/`423`/`409 session_concluded` branches.
- In-progress-games list (wherever it renders, per `009-save-and-continue`): a row whose `available` field (Decision 5) is `false` is rendered greyed out / visually disabled and non-continuable, rather than as a normal actionable row.

**Rationale**: Reuses the one existing, accessible, tested dialog pattern in this codebase rather than introducing a second one (Constitution Principle VIII). Two distinct notice branches (rather than one shared "unavailable" branch) directly reflect Decision 4's two distinct backend outcomes, matching the spec's explicit requirement that the *player*, not just the system internally, understands the difference between "deleted" and "unpublished."

**Alternatives considered**: `window.confirm()` for the delete dialog (rejected — same reasoning as the original draft: the existing unpublish flow already uses a custom accessible dialog, and this feature's confirmation needs richer, multi-sentence copy `window.confirm` renders poorly). A single shared "unavailable" notice component parameterized by reason text only (rejected once two distinct HTTP status codes and distinct downstream actions — no restore possible for delete vs. automatic restore for unpublish — made two small, clearer branches preferable to one branch with conditional logic inside it).

## Decision 8 — No screen-contract amendment needed

**Decision**: Treat the delete action as an extension of the existing "Administrator — stories & configuration" screen contract (constitution.md, Screen contracts) rather than requiring a constitution amendment. The player-facing in-progress-games list and play surface are governed by existing screen contracts (`Adventure select`, `Play surface`) that this feature extends with new states rather than new screens.

**Rationale**: No new screen is introduced — only new actions/states on existing ones (delete row-action; greyed-out list row state; two new play-surface notice states), consistent with how `005-story-publishing-done` added its publish/unpublish row action without amendment.
