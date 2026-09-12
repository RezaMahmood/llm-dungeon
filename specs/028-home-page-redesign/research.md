# Phase 0 Research: Player Home Page Redesign

No `NEEDS CLARIFICATION` markers remain in the Technical Context — the stack, storage, and
testing tooling are all fixed by constitution Principle III and this repo's existing
conventions. The items below record the design decisions made while reconciling the new
mockup with the existing codebase, resolved as part of the spec's Clarifications session.

## Decision 1: Home replaces `/menu`; GamePage keeps only adventure-setup

**Decision**: `HomePage` (new) becomes the element for the `/menu` route, replacing
`MainMenu`. `GamePage` stops rendering its own `StoriesInProgress` / `AdventureList`
sections; it keeps `CharacterNameStep` → `CharacterTypeStep` → session creation, entered with
an adventure already chosen (either from Home's Play action, passing the story id, or by
resuming, which bypasses setup entirely via the existing `resumeSession` call).

**Rationale**: The mockup's nav bar and welcome band only make sense as a landing page; a
second, poorer copy of the same two lists inside `/game` would contradict Home and double the
surfaces a player has to reconcile. `009-save-and-continue`'s behavioral requirements (sort
order, empty-state copy, resume semantics) are preserved — they move to `HomePage`'s
`InProgressList`, not dropped.

**Alternatives considered**: Keep both lists (rejected by the user during clarification —
"leaves two parallel, overlapping session/catalogue UIs"). Make `/game` redirect immediately
to `/menu` and delete the route (rejected: `/game` is still needed as the setup-flow
destination once a story is chosen, and is bookmarked in existing tests/specs as a route).

## Decision 2: Design reference lives at `specs/designs/07-home.html`

**Decision**: Vendor the mockup as `specs/designs/07-home.html` (new number, `02` kept as
historical prior art), add it to `specs/designs/README.md`'s screen list and implementer
notes, and update the constitution's "Adventure select" screen-contract paragraph to name
`07-home.html` as the current acceptance reference for this behavior.

**Rationale**: `06` is already `06-game-setup.html` (a real, shipped, unrelated screen); the
attachment's own filename cannot be reused without collision. Editing the constitution is
unavoidable because it is the document that names `02-story-select.html` as the sole
acceptance reference today — leaving it unedited would make the constitution self-contradict
the moment this feature ships.

**Alternatives considered**: Overwrite `02-story-select.html` in place (rejected by the user
during clarification — loses the historical mockup with no benefit, since the number isn't
otherwise reusable).

## Decision 3: Session deletion is a new, minimal backend capability

**Decision**: Add `PlaySessionService.delete_player_session(session_id, player_id)` (hard
delete of the Cosmos document, following the exact pattern already used by
`delete_active_sessions_for_adventure`) and `DELETE /api/game/sessions/{sessionId}`,
guarded by the existing `authorize_player` middleware and an ownership check
(`session.playerId == player_id`, else `ForbiddenError` → 403, matching every other
player-owned-resource check in this file).

**Rationale**: No endpoint or service method exists today for a player to remove their own
session — only `025-story-delete`'s admin-triggered cascade and the two admin/test-play
delete endpoints exist, neither reachable by a player nor scoped to "my own session only."
Reusing the same Cosmos container and the same delete-by-id primitive already proven by
`delete_active_sessions_for_adventure` needs no new storage design.

**Alternatives considered**: Soft-delete (a `status: "deleted"` flag) — rejected: nothing else
in `PlaySession` uses a tombstone status (`active`/`concluded` are the only two), it would
require every session query to add an exclusion filter, and the spec's FR-009 requires the
story to reappear in "Ready to play" immediately, which a hard delete already satisfies via
`list_player_sessions`'s existing `WHERE status = 'active'` filter with nothing further to
change. Frontend-only stub — rejected by the user during clarification.

## Decision 4: Home's "Play" skips the setup wizard's adventure-selection step

**Decision**: `HomePage` passes the chosen story's id directly into the setup flow (e.g. via
route state / a query param on navigation to `/game`), so `GamePage` starts at
`CharacterNameStep` rather than re-showing an adventure picker Home has already made
redundant.

**Rationale**: `AdventureList` (the existing step-1 card grid) duplicates exactly what
"Ready to play" now shows; making a player choose the same story twice would contradict
FR-006 ("Clicking Play ... MUST take the player into that story's adventure-setup flow")
and SC-002 ("single click from either list").

**Alternatives considered**: Keep `AdventureList` as step 1 inside `/game` regardless
(rejected: redundant click, and two divergent "ready to play" renderings to keep in sync).

## Decision 5: Story blurb is a new, plain admin-authored field

**Decision**: Add `blurb: Optional[str]` to `Story` and `StoryDraft` (`src/backend/models/`)
as a plain field alongside `tone`/`readingLevel` — authored directly by the administrator in
the "Name & cover" wizard step (`StepNameCover.jsx`), not LLM-generated. It joins the
draft's PATCH-able field allowlist in `story_draft_service.py`, is carried through
publish/edit-draft conversion exactly like `tone`, is added to the configuration
file's export/import schema (`story_config_file.py`) so round-tripping a story preserves it,
and is added to `StoryService.list_published_summaries`'s Cosmos projection so Home can read
it.

**Rationale**: The user chose to build this end-to-end rather than ship Home without a
blurb or fake one from LLM-authoring text. Of the two existing patterns for "a field an
administrator sets in the wizard" — `ADMIN_EDITABLE_DERIVED_FIELDS` (LLM-generated by
default, administrator can override) vs. plain fields like `name`/`tone`/`readingLevel`
(always administrator-authored, never generated) — blurb fits the plain pattern: it's
short, player-facing marketing copy with no gameplay derivation, exactly like `name`. This
keeps the change additive and mechanical (one new optional field threaded through existing
plumbing) rather than opening the LLM-generation pipeline for a new derived field.

**Alternatives considered**: LLM-generate the blurb from `worldPrompt`, alongside
`narrativeGuidance`/`startingPoint` (rejected: materially larger scope — new generation
endpoint, new admin-editable-derived-field entry, new regeneration/rate-limit handling —
for a field with no gameplay stakes if it's simply wrong or stale, unlike the two existing
derived fields).
