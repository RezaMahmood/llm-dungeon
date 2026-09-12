# Research: Story and Session Token Usage Tracking

**Date**: 2026-09-11

**Feature**: 026-token-usage

## Decision 1: How token usage escapes `LLMService`

**Decision**: `LLMService._call()` and every public generation method
(`suggest_world_prompt`, `generate_story_config`, `generate_starting_point`,
`generate_gameplay_turn`, `summarize_session_history`) return a
`(payload, tokens_used)` pair, where `tokens_used = input_tokens +
output_tokens` (reasoning tokens are a subset of output tokens already, per
the existing `_call` comment, so they are never added a second time — this
also matches the existing `cost_usd` formula, which only multiplies input
and output counts).

**Rationale**: The OpenTelemetry span already computes these counts per
call; nothing upstream can accumulate them unless `LLMService` hands them
back explicitly. An explicit return keeps every call site's token
attribution visible and testable at the call site, rather than hidden in
mutable state a caller must remember to read at the right moment.

**Alternatives considered**: A stateful `self.last_usage` attribute read by
the caller immediately after each call — rejected as an implicit side
channel that silently misattributes tokens if a future change reorders or
interleaves calls. Re-deriving a story's or session's total from
Application Insights telemetry at read time — rejected: slower, adds a
cross-service dependency to a list-rendering path, and contradicts
spec.md's Assumptions, which call for a persisted running counter for the
same reasons the existing telemetry dashboards (024) are kept separate
from this per-record view.

## Decision 2: Where a story's cumulative total accumulates

**Decision**: `StoryDraft` gains its own `totalTokens` counter, incremented
on every `suggest_world_prompt` call made against that draft (creation or
edit mode). When a draft becomes or updates a `Story`:

- **Creation** (`generate_story`): the new `Story.totalTokens` = the
  draft's accumulated total + the tokens spent on `generate_story_config` +
  `generate_starting_point`.
- **Edit** (`save_draft_to_story`) and **import** (`import_configuration`,
  when it generates missing derived fields): the *existing* story's
  `totalTokens` is **incremented** by the draft's accumulated total (edit
  only) plus any regeneration tokens spent — never replaced, since the
  story already carries prior spend.
- **Backfill** (`ensure_starting_point`, for a `Story` persisted before
  `startingPoint` existed): a successful persist also increments
  `totalTokens` by that call's tokens. In the rare case this backfill loses
  its `_etag` race to a concurrent first session, the losing attempt's
  tokens are not added — an accepted, negligible undercount consistent
  with this project's non-enterprise precision bar (Principle XII), not
  worth a second read-modify-write to close.

**Rationale**: This is every point FR-001/FR-002 name — draft-phase
suggestions, generation, edits, and backfill — using the existing
read-modify-write patterns each of these methods already has, so no new
concurrency mechanism is introduced.

## Decision 3: Test-play tokens count twice, by design

**Decision**: `StoryService.record_test_play(story_id, tokens_used)` is
extended to take the exchange's token count and, in the same
read-modify-write it already performs for `lastTestPlayedAt`, also add
`tokens_used` to `Story.totalTokens`. `TestPlaySessionService` additionally
adds the same `tokens_used` to the `TestPlaySession`'s own `totalTokens`.

**Rationale**: FR-001 explicitly includes admin test plays in the story's
authoring-lifecycle total, and FR-014 requires every gameplay session
(test or real) to carry its own running total. A test-play exchange is the
one call site both requirements cover, so its tokens are attributed twice,
to two different totals that serve two different questions ("what did this
story cost to build" vs. "what did this one test session cost").

## Decision 4: Real player sessions never touch the story's total

**Decision**: `PlaySessionService` adds a real player turn's tokens only to
that `PlaySession.totalTokens` (and its `PlayerInteraction.tokens`), never
to `Story.totalTokens`.

**Rationale**: Confirmed with the requesting user during clarification —
the story's cumulative total stays authoring-lifecycle-only; ongoing player
usage is a distinct, separately reported cost center (the new Sessions
page), consistent with FR-011.

## Decision 5: Summarization tokens count toward the session total, without a turn

**Decision**: When `_summarize_if_due` triggers a `summarize_session_history`
call (every 20 turns, for both `PlaySession` and `TestPlaySession`), its
tokens are added directly to the session's `totalTokens` — no synthetic
turn record is created for them.

**Rationale**: A session's running total (FR-014) must reflect everything
spent on it to be trustworthy, and summarization is a real, periodic LLM
cost tied to that session. It is not itself a player/tester turn, so it
gets no `PlayerInteraction`/`TestPlayExchange` entry — inventing one would
misrepresent what a "turn" is (FR-012's definition: one LLM output produced
from one player/tester input).

## Decision 6: Per-turn tokens are persisted but not sent to players

**Decision**: `PlayerInteraction`/`TestPlayExchange` gain a `tokens` field,
persisted like every other turn field. `get_session_detail_for_player`
(the player-facing saved-game detail endpoint) strips `tokens` from each
turn before returning its response.

**Rationale**: FR-013 only requires that the per-turn count need not appear
in the admin UI; it says nothing about the player-facing API. Persisting it
is required for the session total to be reconstructable and auditable, but
there is no reason to leak internal per-call cost data into a response a
player's browser receives, so it is filtered out at that one boundary
rather than left in only because nothing forbids it. The admin test-play
endpoint (`get_session`, admin-only) needs no equivalent filtering — its
caller is exactly the person who is allowed to see it either way.

## Decision 7: Resolving a session's story name and player/tester email

**Decision**: Neither is snapshotted onto the session document. Both are
resolved live when the Sessions page is loaded:

- **Story name**: the existing story lookup, with a fallback label (e.g.
  "(deleted story)") for a story that can no longer be read — the same
  live-lookup-with-fallback shape `PlaySessionService._resolve_adventure_name`
  already uses for the exact same "story deleted, but the session must
  still render" situation (025-story-delete).
- **Email**: resolved from `ProvisionedAccountEntry` by matching the
  session's `playerId`/`administratorId` (an Entra object id) against each
  entry's `objectId`. Since the account list is small (Principle XII —
  this is not an enterprise user base) and `AccountProvisioningService`
  already has `list_all()`, the Sessions page builds one in-memory
  `objectId -> email` index per load rather than adding a new per-lookup
  query method. A session whose player/tester is no longer provisioned
  shows a placeholder (e.g. "(no longer provisioned)").

**Rationale**: Storing email only in `ProvisionedAccountEntry` — never
duplicated onto every session document — keeps PII in exactly one
access-controlled place (Principle X) and means a corrected or changed
email is reflected everywhere without a backfill. This trades perfect
historical accuracy (what email was valid *at the time* of that session)
for a simpler, single-source-of-truth model consistent with how this
project already treats every other cross-reference (story name, story
availability) as computed live rather than snapshotted.

## Decision 8: The hover affordance uses no new visual component

**Decision**: The last-published-date tooltip is implemented with the
native HTML `title` attribute on the stories list's Status tag, not a new
design-system tooltip/popover component.

**Rationale**: `specs/designs/styles.css` defines no tooltip primitive
today, and Principle VIII bars introducing a new visual-style component
the design system doesn't already provide. A native `title` attribute
carries no visual design of its own — the browser renders it — so it
introduces nothing that principle would need to arbitrate. The stories
list is the only surface changed: `StoryPublishActions.jsx`'s own inline
"last published" text (also rendered in the story wizard's publish step,
the test-play conclusion screen, and the story detail page) is suppressed
only for the list's usage, via a new prop, and is left exactly as before
everywhere else — those other surfaces have no separate Status column to
duplicate against, so nothing forces the same change there.

## Decision 9: The Sessions page needs a constitution amendment

**Decision**: Because the constitution's Screen contracts section
enumerates every screen this product may ship, and "Sessions" is not one
of them, this feature's implementation must include a small constitution
amendment adding an "Administrator — sessions" screen contract entry — no
prototype, deferring visual design to the implementer within Principle
VIII's constraints — following the precedent `012-story-editing-and-review`
set when it added the "Administrator — stories & configuration" entry the
same way.

**Rationale**: The constitution is explicit: "No feature may ship a screen
that is not traceable to a screen contract above or to a documented
amendment extending one." This is a governance step to perform, not a
violation to justify away — see the Constitution Check in plan.md.
