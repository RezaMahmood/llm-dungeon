# Data Model: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Date**: 2026-09-13

**Feature**: `031-sessions-admin-design-spec`

This feature introduces **no new container, no new entity, and no new persisted field**. It
adds a delete operation over two existing entities and one new client-side projection.

---

## Entity: PlaySession (unchanged shape, new lifecycle transition)

**Container**: `playSessions` (existing; partition key `/id`).

No field changes. What is new is a terminal transition the entity did not previously have:

| Transition | Trigger | Effect |
| --- | --- | --- |
| *(any state)* → **deleted** | An administrator confirms deletion on the Sessions screen | The whole document is removed, taking `turns` (the transcript), `checkpoints`, `summary`, `status` and `totalTokens` with it |

### Rules

- Deletion is unconditional on `status`: an `active`, `inactive` or `concluded` session is
  equally deletable (spec FR-006). There is no soft-delete, no tombstone, and no undo.
- Deletion never writes to the session's `Story`. `Story.totalTokens` is not decremented
  (spec FR-009) — a player session never contributed to it in the first place
  (`026-token-usage` FR-011).
- Deletion is idempotent at the document level: a session that vanishes between the read and
  the delete reports as already-removed, matching `delete_player_session`'s existing race
  tolerance.

---

## Entity: TestPlaySession (unchanged shape, new lifecycle transition)

**Container**: `testPlaySessions` (existing; partition key `/id`).

Identical to the above, with two entity-specific rules already established by
`010-story-test-play-done` and preserved here:

- Deleting a test-play session never clears `Story.lastTestPlayedAt` — the test-play marker
  lives on the `Story`, not on the session, so a story that has been test-played stays
  publishable after its test session is cleaned up.
- `Story.totalTokens` already absorbed this session's tokens at the time they were spent
  (`026-token-usage` FR-001) and is not decremented (spec FR-009).

---

## Read model: Session Overview Row (existing, unchanged)

Produced by `SessionOverviewService.list_sessions()`; not persisted. Shape as
`026-token-usage` defined it:

```ts
type SessionOverviewRow = {
  sessionId: string;     // UUID, displayed in full
  sessionType: "player" | "test";
  storyId: string;
  storyName: string;     // "(deleted story)" when the story is gone
  totalTokens: number;
  email: string;         // "(no longer provisioned)" when the account is gone
};
```

### The two sentinel values are part of the contract

`storyName` and `email` are pre-resolved display strings, not raw references: the server
substitutes `DELETED_STORY_LABEL` (`"(deleted story)"`) and `UNPROVISIONED_ACCOUNT_LABEL`
(`"(no longer provisioned)"`) when the referent no longer exists. The client depends on the
first of these twice — to render the Story cell in the design's italic deleted treatment, and
to exclude that row's story from the heading's distinct-story count (research.md Decision 8).
Changing either constant server-side changes the screen's behaviour, so they are contract, not
incidental copy.

`sessionType` is already returned and is not sent back on delete (research.md Decision 1); it
carries no display treatment in the canonical design and gains none here.

---

## Client projection: Sessions heading counts

Derived on every render from the fetched rows; nothing is persisted or requested separately.

| Value | Derivation |
| --- | --- |
| session count | `rows.length` |
| story count | number of distinct `storyName` values, excluding `"(deleted story)"` |
| heading text | `"No sessions"` when the count is 0; otherwise `"{n} session(s) across {m} stor(y|ies)"`, each half singularised independently |

Two sessions of the same story counted once; two *different* deleted stories counted zero
times, not once — the sentinel collapses them, and the design (§4: "Deleted stories are not
counted") asks for exactly that.

---

## Client state: session-removed outcome

Not persisted. A one-shot signal passed as router state from `GamePage` to `HomePage`
(research.md Decision 5), consumed on arrival and cleared so a reload does not refire the
dialog.

```ts
type SessionRemovedState = { sessionRemoved: true };
```

Carries no session id, story name, or account: by the time it is raised the session is gone,
and the message deliberately names neither the actor nor the record (research.md Decision 4).
</content>
