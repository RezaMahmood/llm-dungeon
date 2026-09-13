# Phase 0 Research: Play Surface Design-Spec Conformance

No `NEEDS CLARIFICATION` markers remain in the Technical Context — the stack, storage, and
testing tooling are all fixed by constitution Principle III and this repo's existing
conventions, and no [NEEDS CLARIFICATION] markers were carried over from spec.md (its
Assumptions section already resolved every open question with a documented default). The
decisions below record how those defaults translate into this codebase's existing patterns.

## Decision 1: Chapter identifier is derived from the latest turn, not a new field

**Decision**: The transcript's chapter numeral/kicker (spec.md FR-002) is computed on the
client from data a turn already carries — `progress.current`/`progress.total` for the
numeral, and that same turn's own `locationLabel` as the chapter's title (matching the
canonical design's pairing of "Chapter three — The keeper's stairs" with a "Where you are:
The keeper's stairs" status panel). No new turn field is introduced.

**Rationale**: The backend's `PlayerInteraction`/turn shape (`src/backend/models/play_session.py`)
has never carried a chapter title of its own — only `locationLabel`, `goalLabel`, and
`progress`. Adding a server-authored chapter title would be new backend surface this
frontend-conformance feature does not need: the design's own two labels ("Chapter three" and
"The keeper's stairs") already read as the same place, just narrated at two altitudes.

**Alternatives considered**: Add a `chapterTitle` field to `Story`/turn generation (rejected —
new backend/LLM-prompt surface for a value the existing `locationLabel` already supplies;
out of proportion to a UI-conformance feature). Show only the numeral, no title (rejected —
drops half of the canonical design's chapter kicker for no reason).

## Decision 2: Spelling-forgiveness runs client-side against the turn's own vocabulary

**Decision**: A submitted command is compared, client-side, against the current turn's
`suggestedActions` (already present in every turn payload) using a simple near-miss check
(e.g. edit-distance against each suggested action's words). A likely near-miss produces the
non-blocking suggestion note (spec.md FR-006/FR-007); the move itself is still submitted and
narrated exactly as typed. No backend or LLM-service change.

**Rationale**: The canonical design's own data contract (`03-play-spec.md` §11) shows
`spellingHint?: { suggestion: string }` as part of the view the play screen renders, but
`sessions.py`'s `_narrative_dict` and `PlayerInteraction` carry no such field today, and nothing
in issue #332 or its attachments asks for a new backend judgment call — the design spec
explicitly scopes itself to what the play screen shows, not how a misspelling is detected.
Constitution readability rule #4 already requires forgiving input; a client-side check against
data already on the page satisfies it without new scope.

**Alternatives considered**: Have the LLM narrative service flag suspected misspellings and
return them as a new turn field (rejected for this feature — a real backend/prompt-engineering
change, out of proportion to a UI-conformance issue; spec.md's Assumptions section leaves this
door open for a future feature to add without changing today's requirements). Skip spelling
forgiveness entirely (rejected — explicitly required by both the design spec and the existing,
currently-unimplemented constitution readability rule #4).

## Decision 3: "Stuck? Get a hint" discloses static, generic guidance in place

**Decision**: The status panel's existing (currently inert) "Stuck? Get a hint" button becomes
a disclosure toggle that reveals a short, generic, non-story-specific hint ("try one of the
suggested actions, or describe what you'd do in your own words — spelling doesn't have to be
perfect") directly beneath it, and hides it again on a second click. No network call, no
story-specific hint content.

**Rationale**: `03-play-spec.md` §12 explicitly places "the hint content itself" out of scope,
and the constitution's own "Play surface" screen contract already requires "a hint action"
without specifying its content — so the only requirement this feature must satisfy is that a
hint action exists and works in place (FR-009), which a static disclosure satisfies today.
Constitution Principle XI (Implementer Design Latitude) permits this judgment call without
a pre-implementation sign-off.

**Alternatives considered**: Call an LLM/backend endpoint for a story-aware hint (rejected —
real new backend + prompting surface, explicitly out of scope per the design spec itself).
Leave the button inert (rejected — fails FR-009 and the constitution's existing "hint action"
requirement).

## Decision 4: Header Refresh reuses `RefreshContext`/`getSession`, exactly as `NavBar` does elsewhere

**Decision**: `PlayPage` publishes a refresh handler through the existing `RefreshContext`
(`usePublishRefresh`, the same hook every other authenticated page already uses), and
`TitleBar` renders the shared `RefreshButton` from that context exactly as `NavBar` already
does, ahead of the other trailing actions per `03-play-spec.md` §3's header ordering. The
handler re-calls the existing `getSession(token, sessionId)` (already used by `GamePage`'s
resume path) and replaces the in-memory turn history/status with what comes back.

**Rationale**: `019-spa-refresh-button` already defines "refresh" as "re-fetch this screen's
own data without a full reload" and already wires `RefreshContext` through
`AuthenticatedLayout` to both `NavBar` and `TitleBar`'s siblings; `TitleBar` is simply the one
place that never published or read it. Reusing `getSession` avoids inventing a second way to
fetch the same session shape `GamePage` already fetches on resume.

**Alternatives considered**: A dedicated "resync" endpoint (rejected — `GET
/api/game/sessions/{sessionId}` already returns everything needed; no gap to fill). Reload the
whole SPA (rejected — contradicts `019-spa-refresh-button`'s entire premise and would drop
the player out of the play screen).

## Decision 5: Page-scoped styling moves into `Play.css`, mirroring `Home.css`

**Decision**: The inline `style={{...}}` objects that currently encode this screen's
structural layout (flex/grid rules, padding, the 292px status-panel width, the transcript's
64ch cap) move into a new `src/frontend/src/components/Play/Play.css`, imported once by
`PlayPage`/`AdminStoryTestPlayPage`. Values remain token-based (`var(--color-*)` etc.); no
literal hex/pixel-outside-token values are introduced.

**Rationale**: `028-home-page-redesign` established the precedent (`Home.css`) for exactly
this situation — "a small number of narrowly scoped layout or behavior utility classes with
no visual-design opinion of their own" (constitution, UI Design System Requirements) — and
the play surface's inline styles were flagged as the thing issue #332 asks to fix
("conformance," not just visual parity).

**Alternatives considered**: Leave the structural rules as inline styles and only fix the
missing affordances (rejected — issue #332 and spec.md FR-014 both call for design-system
conformance, and the inline-style duplication across `PlayPage`/`AdminStoryTestPlayPage` is
exactly the kind of screen-specific reimplementation Principle VIII warns against).
