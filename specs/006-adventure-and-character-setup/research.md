# Phase 0 Research: Adventure and Character Setup

**Feature**: 006-adventure-and-character-setup | **Date**: 2026-08-31

The spec has no `NEEDS CLARIFICATION` markers (clarification round already completed — see
spec.md Clarifications). This document instead records the technical decisions needed to move
from spec to design, each with rationale and rejected alternatives.

## Decision 1: No new persisted entity

**Decision**: Reuse the existing `Story` model (`src/backend/models/story.py`) and its
`characterTypes: list[CharacterType]` field, and the existing Cosmos `Stories` container, via
the existing `StoryService`. No new "Play Session Setup" entity is persisted by this feature.

**Rationale**: The spec's "Play Session Setup" key entity (adventure + name + character type) is
explicitly scoped as *ephemeral, pre-play state* — the spec says the resulting play session
itself is owned by `008-core-gameplay`. Persisting a separate setup-state entity here would be
speculative infrastructure for a value that only needs to exist for the duration of one HTTP
request (`POST /api/game/start`'s request body) plus whatever client-side state React holds
between steps. Constitution Principle IV (Simplicity Over Premature Scale) rules out adding
storage ahead of a stated need.

**Alternatives considered**:
- A `PlaySessionSetup` Cosmos entity, written as the player progresses through the three steps
  and read back by `008-core-gameplay`. Rejected: `008-core-gameplay` is a separate, not-yet-
  planned spec: this feature owning the shape of a hand-off entity for it is exactly the kind
  of premature coupling Principle IV warns against. When `008` is planned, it can define
  whatever request/entity shape it needs `POST /api/game/start`'s successful response to carry.

## Decision 2: New player-scoped endpoint `GET /api/game/adventures`

**Decision**: Add a new endpoint rather than reusing or relaxing the existing admin-only
`GET /api/manage/stories` (`004-story-creation-done`).

**Rationale**: `GET /api/manage/stories` is gated by `authorize_admin` and returns the
admin-shaped summary (`id`, `name`, `published`, `createdAt` — unpublished stories included,
per `story_service.list_summaries()`). Players must never reach an admin-gated endpoint
(Constitution Principle II), and the player-facing list must show *only* published adventures
(FR-001, FR-006) with player-relevant fields (name, tone, session length, reading level — per
the `02-story-select.html` design reference) rather than admin bookkeeping fields like
`published`/`createdAt`. A distinct endpoint keeps the admin and player read paths — and their
authorization gates — independent, so a future change to one (e.g., adding an admin-only field)
can't leak into the other.

**Alternatives considered**:
- Add a `?published=true` query param to `GET /api/manage/stories` and relax its authorization
  to also accept `Player`. Rejected: mixes two different authorization policies and two
  different response shapes on one endpoint, which is harder to reason about and test than two
  small, single-purpose endpoints — and risks an admin-only field leaking to players by
  omission in a future edit.

## Decision 3: New `authorize_player` middleware

**Decision**: Add `src/backend/api/game/middleware.py::authorize_player`, mirroring
`src/backend/api/admin/middleware.py::authorize_admin`'s shape exactly (same
`authenticate_with_email` → `AccountProvisioningService.authorize_sign_in` → role-check
pipeline, substituting `"Player"` for `"Administrator"`), returning the same
`(is_authorized, user_oid, error_response_or_None)` tuple contract.

**Rationale**: `POST /api/game/start` already inlines this exact check (see
`src/backend/api/game/start.py`'s current body — authenticate, authorize sign-in, check
`"Player" not in entry.roles`). The new `GET /api/game/adventures` endpoint needs the identical
check. Extracting it into a shared middleware function (rather than duplicating the inline
block a second time) follows the same DRY pattern the admin API already established, and keeps
both endpoints' authorization behavior guaranteed identical by construction.

**Alternatives considered**:
- Duplicate the inline check into the new endpoint, as `start.py` currently does inline.
  Rejected: two independent copies of a security-critical check drift silently; the admin side
  already avoided this by centralizing in `admin/middleware.py`.

## Decision 4: Extend `POST /api/game/start` with server-side setup validation

**Decision**: Extend the existing placeholder to accept `{ adventureId, characterName,
characterType }` in the request body and validate, in order:
1. `adventureId` refers to a `Story` that exists and has `published == True` (else 404/409 —
   exact code decided in contracts/api.md).
2. `characterName` is non-blank after trimming whitespace, and ≤50 characters (FR-002).
3. `characterType` is one of the `name` values in that story's `characterTypes` list (FR-003).

All three must pass before returning a success response; any missing/invalid field is reported
back identified by name (FR-005). The endpoint still does **not** create a play session — that
remains `008-core-gameplay`'s responsibility; a 200 response here means "setup is valid," not
"a session now exists."

**Rationale**: Constitution Principle II requires server-side enforcement — a client-side-only
check on the 3-step wizard would be bypassable by calling the API directly. FR-004 requires the
system to *prevent* play starting on incomplete/invalid setup, which for an HTTP API means the
endpoint itself must be the enforcement point, not just the frontend's step-gating UI.

**Alternatives considered**:
- Validate only on the frontend (step-by-step client-side gating) and leave `POST
  /api/game/start` accepting whatever the client sends. Rejected: directly violates
  Constitution Principle II ("a client-side check alone is never sufficient").
- Add a separate `POST /api/game/validate-setup` endpoint distinct from `start`. Rejected:
  unnecessary two-call round trip for what is otherwise one atomic gate; `start` already exists
  as exactly the right seam (per the prior session's codebase research) and its current
  placeholder response ("Game start not yet implemented") already signals it's the intended
  extension point once `008-core-gameplay` lands.

## Decision 5: 3-step flow lives inside the existing `/game` route, no new route

**Decision**: Build the adventure → name → character-type flow as the content of the existing
`GamePage.jsx` (reached via `/game`, already linked from `MainMenu.jsx`'s "start a new game"
action), replacing its current placeholder ("Game features loading…"). No new React Router
route is added.

**Rationale**: `/game` is already the player's entry point for starting a game session
(confirmed: `MainMenu.jsx` navigates there via `GameMenuItem`), and its current content is
explicitly a placeholder pending exactly this kind of feature. `008-core-gameplay`'s actual play
surface (`specs/designs/03-play.html`) will presumably also live at or under this route once
setup is complete — introducing a separate route for setup now would need to be reconciled with
that later anyway.

**Alternatives considered**:
- A new dedicated route (e.g., `/game/setup`), with `/game` reserved for the eventual play
  surface. Rejected: adds route/navigation complexity (an extra redirect step after setup
  completes) not justified by any current requirement — Constitution Principle IV.

## Decision 6: Character-type reset semantics on adventure change (implementation note)

**Decision**: This is React component *state*, not persisted server state — when the player
changes their selected adventure, the frontend clears `characterType` from local state (FR-004a)
while retaining `characterName`. No backend call is needed to "reset" anything, since nothing is
persisted until `POST /api/game/start` is called with the final, complete selection.

**Rationale**: Per Decision 1, no setup-in-progress state is persisted server-side, so this
FR is purely a client-side state-management concern, confirmed already resolved in spec
clarifications (Session 2026-08-29, Q2).

**Alternatives considered**: None — this follows directly from Decision 1; recorded here only
to make the implication of that decision explicit for the tasks phase.
