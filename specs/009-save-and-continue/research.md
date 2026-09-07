# Phase 0 Research: Save and Continue

**Feature**: 009-save-and-continue | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

The spec's five clarifications (Session 2026-09-06) already resolved the behavioural
questions. What remains is deciding how each resolved behaviour lands on top of the
`008-core-gameplay-done` code that shipped in `#237` — which already persists a `PlaySession`
after every turn, already owns single-active-session semantics (`isActiveForPlayer`), and
already renders an (inert) "Save a checkpoint" button in `TitleBar`. No NEEDS
CLARIFICATION markers remain in Technical Context.

---

## Decision 1: Store checkpoint markers as an embedded array on `PlaySession`

**Decision**: Add a `checkpoints: list[CheckpointMarker]` field to the existing
`PlaySession` document (container `playSessions`), append-only, alongside `turns`. No new
Cosmos container, no new partition key, no Terraform change.

**Rationale**: A marker is ~3 short fields that only ever exist in the context of one
session, is only ever read when that session is read, and can never outlive it. Embedding
mirrors how `008` already embeds `PlayerInteraction` in `turns` and how `004` embeds
story-creation exchanges. It also makes "record a checkpoint" a single conditional
document write with the ETag pattern `_release_claim`/`_deactivate_other_active_sessions`
already use — no second write, no cross-document consistency question.

**Alternatives considered**:
- *A new `checkpoints` container*: a second container, a second partition-key decision,
  and a second write per save, for data with no independent lifetime. Rejected under
  Principle IV (YAGNI) — nothing reads markers across sessions.
- *A separate document in `playSessions`*: avoids growing the session document but gives
  up the single-write atomicity and requires a query per session read.

---

## Decision 2: A marker stores the location label and the save time separately, not one pre-formatted string

**Decision**: `CheckpointMarker` is `{ label, turnNumber, createdAt }`, where `label` is
the `locationLabel` of the session's latest turn at the moment of the save (falling back
to `"Your story"` when that turn carries no location), `turnNumber` is that turn's number,
and `createdAt` is an ISO-8601 UTC timestamp. The player-facing string ("The keeper's
stairs · 6 Sep") is composed in the browser from those two fields.

**Rationale**: Spec FR-003 requires the label be generated "from the game's current
in-fiction location and the time of the save" — those are exactly these two fields. Keeping
them separate avoids formatting a date server-side in a timezone and locale the server does
not know, which is the same reason `lastInteractionAt` is already returned raw and rendered
client-side. `turnNumber` costs nothing to store and makes a marker independently
interpretable when read back.

**Alternatives considered**:
- *Server composes a single display string*: forces a server-side locale/timezone guess and
  freezes the presentation into stored data.
- *Store only `createdAt`, re-derive the location on read*: the location would drift as the
  player kept playing, so the marker would stop describing the point it marked.

---

## Decision 3: Two new read endpoints — a list for the continue screen, a detail read for rehydration

**Decision**: Add `GET /api/game/sessions` (the player's own unconcluded sessions, newest
activity first, each with the adventure name, character name, latest location, progress,
`lastInteractionAt`, and `isActiveForPlayer`) and `GET /api/game/sessions/{sessionId}`
(one session in full, including every turn, so the play surface can be rebuilt exactly).

**Rationale**: `008` ships no read endpoint at all — `PlayPage` only ever holds turns it
saw created in the same browser session, which is precisely why resuming across visits does
not work today. The two endpoints are separate because their payloads differ by orders of
magnitude: the list must stay small enough to render a screen (no `turns`), while the detail
read is the one place the full narrative history is needed. Ownership is enforced
server-side in both (`playerId == authenticated user`), satisfying FR-001 and Principle II.

**Alternatives considered**:
- *One endpoint returning full sessions*: sends every turn of every in-progress game to
  render a list of two rows.
- *Reuse `POST .../resume`'s response*: it returns only `{status, sessionId}`, and widening
  it would change a contract `008` already tests, for no gain over a plain `GET`.

---

## Decision 4: The continue list resolves adventure names by batch-reading the distinct stories it references

**Decision**: `list_player_sessions` collects the distinct `adventureId` values across the
returned sessions and reads each once through `StoryService.get_story`, mapping the name
onto every row that references it.

**Rationale**: The design's row is "adventure title · chapter · last played · location", so
the title has to come from the `stories` container — `PlaySession` stores only
`adventureId`. Distinct-ID batching means a player with five sessions across two adventures
does two story reads, not five. A story that has since been unpublished or deleted still
resolves for its own player (they are resuming a game they already started, not browsing
the catalogue); a missing story falls back to a neutral `"Adventure"` label rather than
hiding the row, so a player can never lose access to a game they have in progress.

**Alternatives considered**:
- *Denormalise the adventure name onto `PlaySession` at creation*: cheaper reads, but the
  name would go stale when an adventure is renamed, and it changes `008`'s write path.
- *A cross-partition `IN` query on `stories`*: more RU than N point reads for the small N
  this feature can produce, and a new query shape to test.

---

## Decision 5: Resuming an already-active game does not call `POST .../resume`

**Decision**: The continue screen reads `isActiveForPlayer` from the list row. When it is
`true`, the client goes straight to the play surface via `GET /api/game/sessions/{id}`.
When it is `false`, it calls `POST .../resume` first, and treats a
`409 already_active` response as success rather than an error (covering a list that went
stale between render and click).

**Rationale**: The spec's edge case requires that resuming the already-active game "succeeds
and simply returns them to it... with no error shown", while `008`'s `resume_session`
deliberately raises `AlreadyActiveError` → `409 already_active`. Deciding client-side keeps
`008`'s endpoint contract and its tests untouched, and the 409 fallback means correctness
does not depend on the list being fresh.

**Alternatives considered**:
- *Make `POST .../resume` idempotent (200 when already active)*: arguably nicer as an API,
  but it rewrites a shipped contract and its integration tests to serve one client-side
  branch this feature can take on its own.
- *Always call resume and ignore any 409*: hides genuine `session_concluded` 409s behind the
  same swallow, and spends a write on the common case.

---

## Decision 6: "A game is in progress" for the logout prompt means an active, unconcluded session

**Decision**: The sign-out control asks `GET /api/game/sessions` and prompts only when at
least one returned session has `status == "active"` **and** `isActiveForPlayer == true` —
the player's current game. Concluded games never appear in that list, so they can never
trigger the prompt (spec Edge Case 2, FR-004).

**Rationale**: Sign-out lives only in `NavBar`, which `022-persistent-nav-redesign` removed
from the play screen, so "in progress" cannot mean "the play surface is on screen" — the
player is by definition somewhere else when they reach the control. The server-side
active-game flag `008` already maintains is the accurate, non-client-trusted answer to "are
you currently in a game", and reusing the list endpoint avoids inventing a second one.

**Alternatives considered**:
- *Prompt whenever any unconcluded session exists*: would nag a player about a game they
  set aside weeks ago and left deliberately, which is not "currently in a game".
- *A dedicated `GET /api/game/sessions/active` endpoint*: a third endpoint returning a
  strict subset of the list this feature already builds.
- *Add a sign-out control to the play surface*: `specs/designs/03-play.html`'s header has
  only "Save a checkpoint" and "Pause & exit"; adding a third control there would break the
  screen contract (Principle VIII) to solve a problem the route structure does not have.

---

## Decision 7: A failed checkpoint never holds the player in place

**Decision**: Every checkpoint write is fire-and-report. If it fails, the surface that
requested it shows a `role="status"` notice — "We couldn't record that checkpoint, but your
progress is safe" — and the action the player actually asked for (return to the stories
screen, or sign out)
completes anyway, with no confirm step and no retry gate. On the sign-out path the notice
renders in the prompt and `logoutRedirect()` is invoked in the same update, so the player is
never asked to acknowledge anything before leaving.

**Rationale**: FR-006a forbids blocking, delaying, or reversing the departure, and the
marker is cosmetic — the turns themselves were persisted by `008` as they happened. Holding
a player who is trying to leave a shared machine in a modal over a failed label would be the
worst possible trade. The accepted limitation is that on the sign-out path the notice is
only briefly visible before the redirect navigates away; it is still rendered and asserted in
tests, and the player-facing consequence (no marker) is genuinely nil.

**Alternatives considered**:
- *"Sign out anyway" confirmation on failure*: blocks departure, contradicting FR-006a.
- *Retry silently until it succeeds*: unbounded delay on exactly the path where the player
  is trying to leave.
- *Fail silently*: rejected by the spec's clarification (Option C was declined in favour of
  telling the player).

---

## Decision 8: The checkpoint write is a read-modify-write with one retry on ETag conflict

**Decision**: `record_checkpoint` point-reads the session, appends the marker, and writes
with `MatchConditions.IfNotModified` on the read ETag. On a precondition failure it retries
once from a fresh read; a second failure surfaces as a normal checkpoint failure (Decision
7), not an error the player must resolve.

**Rationale**: A checkpoint can race a turn write — the player can tap "Save a checkpoint"
while the previous action's narrative is still being generated. The ETag pattern is what
every other write in `play_session_service.py` already uses, so a conflict cannot silently
clobber a turn. One retry absorbs the realistic single-writer race; more retries would
reintroduce the delay Decision 7 rules out.

**Alternatives considered**:
- *Reject the save while `interactionInProgress` is true*: a `409` the player would have to
  understand and retry, for a save that could simply land a moment later.
- *Unconditional write*: would drop the turn that landed in between. Never acceptable —
  losing a turn contradicts the constitution's "Exiting never loses a turn already taken".

---

## Decision 9: The continue list renders at the top of the existing `/game` screen

**Decision**: A "Stories in progress" section is added above "01 — Choose an adventure" on
`GamePage`, and resuming hands off to `PlayPage` in place, exactly as starting a new game
already does.

**Rationale**: `specs/designs/02-story-select.html` is one screen with two stacked sections
— "stories in progress" then "stories you haven't opened" — and `GamePage` already renders
the second of them. Putting the first above it completes that screen contract with no
routing change, and reuses the handoff into `PlayPage` that `GamePage` already performs.

**Alternatives considered**:
- *A new `/continue` route*: splits one designed screen into two, and adds a route whose
  only content is a list the design puts on an existing page.
- *Put it on `/menu`*: `MainMenu` is the capability chooser (Play / Admin), not the story
  picker; the adventure list it would sit beside lives on `/game`.

---

## Decision 10: `PlayPage` gains a turn history, published save handler, and no new header

**Decision**: `PlayPage` accepts `initialTurns` (an array) instead of only
`initialNarrative`, and publishes `onSaveCheckpoint` through `PlayTitleContext` alongside
the `storyTitle`/`onPauseExit` it already publishes. `TitleBar`'s existing
`onSaveCheckpoint` prop gains the same published-value fallback its `onPauseExit` already
has.

**Rationale**: `TitleBar` already renders the "Save a checkpoint" button from
`03-play.html`; it is inert today only because nothing supplies a handler. Wiring it
through the context that exists for exactly this purpose keeps FR-016's rule that the play
surface never grows a second header, and keeps this feature from restyling a shipped screen.
`initialTurns` is the minimum change that lets a resumed game render its whole history.

**Alternatives considered**:
- *A separate resumed-play route/component*: two components rendering the same screen,
  drifting apart.
- *Have `PlayPage` fetch its own session by id*: pushes a second loading state into a
  component that currently receives its data ready-made, and duplicates the fetch
  `GamePage` must do anyway to decide what to render.
