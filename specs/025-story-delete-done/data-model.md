# Data Model: Story Delete

**Date**: 2026-09-07

**Feature**: Story Delete (025-story-delete)

This feature introduces no new entity and no new container. It adds a terminal, destructive lifecycle operation to the existing `Story` entity (`004-story-creation-done`, extended by `005-story-publishing-done`) and, critically, **two different** treatments of the existing `PlaySession` entity (`008-core-gameplay-done`, extended by `009-save-and-continue`) depending on *why* its story became unavailable — deleted, or merely unpublished. These two outcomes are not interchangeable and must be kept distinct throughout the implementation.

---

## Entity: Story (lifecycle extension — no schema change)

**Container**: `stories` (existing; partition key `/id`).

No new or changed properties. `delete_story(story_id)` removes the row from the container entirely (`delete_item(item=story_id, partition_key=story_id)`) rather than setting a field — see research.md Decision 1 for why this differs from `published`'s flag-based model. `unpublish` (existing, `005-story-publishing-done`) is entirely unchanged by this feature.

### State Transitions

```
(any state: published=true or published=false, per 005-story-publishing-done)
  → [administrator confirms delete]
      → the Story row no longer exists.
        - Every active (status='active') PlaySession referencing this story's id is also
          permanently removed (see PlaySession → Cascade on Delete below).
        - Any subsequent read (GET .../{storyId}, publish, unpublish, edit-drafts, configuration,
          another delete) for this id returns 404 not_found, identical to a story id that never
          existed (FR-013).

  → [administrator unpublishes] (existing 005 behavior, UNCHANGED by this feature)
      → published=false. No PlaySession is touched (FR-005). Every PlaySession referencing
        this story's id becomes non-continuable, computed live (see PlaySession → Live
        Availability below) — not by any write to the PlaySession itself.

  → [administrator re-publishes an unpublished story] (existing 005 behavior, UNCHANGED)
      → published=true. Every PlaySession referencing this story's id automatically becomes
        continuable again, computed live — no write to the PlaySession itself (FR-011).
```

### Validation Rules

- `delete` never accepts a request body; there is nothing to validate beyond the `storyId` route parameter and admin authorization.
- `delete` has no server-side precondition — it does not depend on `published`, the FR-008 publish-gate state, or anything else (FR-003). The only client-side gate is the FR-002 confirmation prompt, enforced before the request is ever sent (not a server precondition, consistent with how `unpublish`'s FR-013 confirmation already works).
- Deleting a nonexistent `story_id` (never existed, or already deleted) returns `404`, the same shape as the existing `GET /api/manage/stories/{storyId}` 404.

---

## Entity: PlaySession — two distinct, non-interchangeable outcomes (no schema change)

**Container**: `playSessions` (existing; partition key `/id`, per `_read_item`'s `partition_key=session_id`).

**No new or changed field is added to `PlaySession` by this feature.** The two outcomes below are implemented entirely by (a) whether the row is deleted, and (b) live-reading the *current* `Story.published` value at the moment a session is acted on — never by a stored flag on the session itself.

### Cascade on Delete (permanent, irreversible)

```
[Story S is deleted]
  → for every PlaySession P where P.adventureId == S.id and P.status == 'active':
      → P is PERMANENTLY DELETED from the playSessions container (FR-004).
        - P no longer appears in list_player_sessions() for its owning player (FR-010) —
          removal alone is sufficient, no new list-side filtering needed, since the row is gone.
        - If that player's own next request for P (a turn, a resume, or a detail read) is
          already in flight or arrives after P's removal, it fails with SessionNotFoundError,
          mapped to the "story_deleted" response (research.md Decision 4).
        - There is no path back: P cannot be un-deleted, unlike the unpublish case below.
  → PlaySessions with status == 'concluded' for this adventureId are NOT touched (Edge Cases —
    finished games are history, not "in progress").
```

### Live Availability on Unpublish (never mutates the row; fully reversible)

```
[Story S is unpublished]              (no write to any PlaySession occurs)
  → for every PlaySession P where P.adventureId == S.id and P.status == 'active':
      → P's row is completely unchanged.
      → The NEXT TIME P is used — a turn submitted, a resume, a detail read, or a
        list_player_sessions() call for P's owning player — the current S.published is
        read fresh:
          - submit_interaction / resume_session / get_session_detail_for_player against P:
            blocked with StoryUnpublishedError → "story_unpublished" response (409),
            without altering P (research.md Decision 4).
          - list_player_sessions(): P's row is still returned, with available=false
            (research.md Decision 5) — greyed out client-side, not omitted.

[Story S is later re-published]        (no write to any PlaySession occurs)
  → The very next read of any kind against any PlaySession P for S automatically reflects
    S.published == true again — normal turn/resume/detail behavior resumes, and
    list_player_sessions() returns available=true for P — with no separate restore
    action (FR-011).
```

### Validation Rules

- The cascade-delete query is cross-partition (`adventureId` is not the partition key), matching the existing `list_player_sessions`/`_deactivate_other_active_sessions` query shape in `play_session_service.py`.
- The cascade-delete runs for every player who has an active session against the deleted story, not just the requesting administrator's own view (FR-004 — "regardless of which player owns it").
- The live-availability check (`story.published`) is evaluated fresh on every relevant request; it is never cached on the `PlaySession` document, so it can never go stale between an unpublish/re-publish and the player's next request.
- A session already `status == 'concluded'` is exempt from both the cascade-delete and the live-availability check — its outcome does not change based on its story's later published/deleted state (Edge Cases).

## Storage Model

No new container. Query/mutation patterns added:

```
Story delete:
  container.delete_item(item=storyId, partition_key=storyId)   # ~1 RU

PlaySession cascade-delete (per deleted story):
  container.query_items("SELECT c.id FROM c WHERE c.adventureId = @id AND c.status = 'active'", ...)
  container.delete_item(item=row.id, partition_key=row.id)     # once per matching row

PlaySession live-availability check (per turn/resume/detail request against an existing session):
  StoryService.get_story(session.adventureId)                  # already an existing call in
                                                                #   _generate_and_persist_turn;
                                                                #   this feature only adds a
                                                                #   `not story.published` branch
                                                                #   alongside the existing
                                                                #   `story is None` branch

list_player_sessions augmentation:
  StoryService.get_adventure_summary(adventureId) (or equivalent batched query) extended to
  also surface `published`, reusing the existing per-adventure-id batch resolution that already
  fetches each row's adventure name — no new query shape, one more projected field.
```

**Cost**: One story delete plus, at most, one delete per player currently mid-game on that story — negligible at this project's scale (Principle IV); no new indexing or container-level changes required since `adventureId` and `status` are already queried together by existing code, and the live-availability check reuses an existing point read.
