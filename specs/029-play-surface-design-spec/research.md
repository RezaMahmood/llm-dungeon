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

## Decision 2: The "Stuck? Get a hint" control ships disabled; its guidance is a separate feature

**Decision**: `StatusPanel` gains the "Stuck? Get a hint" control the canonical design places
between the progress section and the autosave notice — built from the design system's
`btn btn-secondary btn-block`, in the same position and treatment — rendered `disabled` with
an adjacent `.play-hint-pending` note reading "Hints are coming soon." The control performs no
action in this feature. What a hint says, and where it comes from, is specified separately.

**Rationale**: spec.md's *Scope note* governs: the design shows this control, nothing behind it
exists on `origin/main` (`StatusPanel.jsx` has no such button — the string lives only in
`specs/designs/03-play.html`), so this feature builds the control and defers the behaviour.
`disabled` is what makes the deferral honest: the design system already themes the disabled
state (reduced opacity, `not-allowed` cursor, `.btn:disabled`), a disabled `<button>` is
conveyed natively to assistive technology, and the adjacent note satisfies the constitution's
"every failure or dead-end state offers a next action" by saying plainly what is coming. An
enabled control that does nothing would fail that rule and mislead the player.

**Alternatives considered**: Reveal a static, generic hint written here (rejected — the
invented stand-in behaviour spec.md's *Scope note* exists to prevent; it would have to be
unpicked when the real hint ships). Omit the control until its feature lands (rejected — the
panel's layout and spacing do not match the canonical design without it, which is this
feature's whole purpose). Call an LLM/backend endpoint for a story-aware hint (rejected —
that *is* the separate feature).

**Constitution note**: the "Play surface" screen contract requires "a hint action", which a
disabled control does not yet deliver. plan.md's Constitution Check records this as a named,
time-boxed deferral rather than a PASS. The broader problem — the constitution stating
functional requirements that belong in feature specs — is tracked as issue #340.

## Decision 3: Header Refresh reuses `RefreshContext`/`getSession`, exactly as `NavBar` does elsewhere

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
fetch the same session shape `GamePage` already fetches on resume. spec.md's *Scope note* does
not defer this one: the implementation pattern already exists, so wiring it is ordinary work.

**Alternatives considered**: A dedicated "resync" endpoint (rejected — `GET
/api/game/sessions/{sessionId}` already returns everything needed; no gap to fill). Reload the
whole SPA (rejected — contradicts `019-spa-refresh-button`'s entire premise and would drop
the player out of the play screen).

## Decision 4: Page-scoped styling moves into `Play.css`, mirroring `Home.css`

**Decision**: The inline `style={{...}}` objects that currently encode this screen's
structural layout (flex/grid rules, padding, the 292px status-panel width, the transcript's
64ch cap) move into a new `src/frontend/src/components/Play/Play.css`, imported once by
`PlayPage`/`AdminStoryTestPlayPage`. Each value is translated to the nearest design token
(`--space-*`, `--font-*`, `--color-*`) from the app's vendored token layer
(`src/frontend/src/styles/designTokens.css`, whose source is `specs/designs/styles.css`); a
value with no token — the 292px panel width, the 64ch measure — is carried as a literal and
named in `Play.css` as a deliberate exception. The `.play-*` classes are additive layout-only
modifiers: every control keeps its design-system class (`btn btn-secondary`, `input`,
`btn btn-primary`), so the four mandated interaction states are never restyled locally.

**Rationale**: `028-home-page-redesign` established the precedent (`Home.css`) for exactly
this situation — "a small number of narrowly scoped layout or behavior utility classes with
no visual-design opinion of their own" (constitution, UI Design System Requirements) — and
the play surface's inline styles were flagged as the thing issue #332 asks to fix
("conformance," not just visual parity). A literal 1:1 copy of today's inline pixel values
would defeat that: the constitution makes "a magic pixel value that a token already covers" a
review blocker.

**Alternatives considered**: Leave the structural rules as inline styles and only fix the
missing affordances (rejected — issue #332 and spec.md FR-012 both call for design-system
conformance, and the inline-style duplication across `PlayPage`/`AdminStoryTestPlayPage` is
exactly the kind of screen-specific reimplementation Principle VIII warns against).

## Decision 5: The segmented progress bar is promoted to a shared class, not re-forked

**Decision**: The chapter-progress bar the status panel needs (spec.md FR-006) is the same
control `028-home-page-redesign` already shipped as `.home-pcard-bars` / `span.filled` in
`src/frontend/src/components/Home/Home.css`. That rule is promoted into the app's shared token
layer as `.progress-bars` / `span.filled`, and both Home and the play surface consume it;
`Home.css` keeps `.home-pcard-bars` only as a positioning wrapper.

**Rationale**: Principle VIII forbids introducing "a component or visual-style class
duplicating one" the system already provides. Two independent segmented bars with the same
accent/neutral treatment would drift the first time either is restyled.

**Alternatives considered**: Define `.play-segments`/`.play-segment` in `Play.css`
(rejected — the duplication above). Leave Home's rule alone and import `Home.css` from the
play surface (rejected — couples two unrelated screens through a page-scoped stylesheet).
