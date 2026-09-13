# UI Contract: Play Surface Design-Spec Conformance

This feature changes no HTTP contract — every endpoint the play surface calls
(`GET /api/game/sessions/{sessionId}`, `POST /api/game/sessions/{sessionId}/interactions`,
`POST /api/game/sessions/{sessionId}/resume`, `POST /api/game/sessions/{sessionId}/checkpoints`)
is unchanged (data-model.md). What changes is the **component contract** between
`PlayPage` and the components it composes, and the markup/class contract each component
presents for styling and testing.

All `.play-*` classes below are additive layout-only modifiers. Every control keeps the
design-system class it already carries (`btn btn-secondary`, `input`, `btn btn-primary`), so
hover, pressed, `:focus-visible` and disabled remain the shared layer's (research.md
Decision 4).

## `StoryPane`

**Props**: `turns: Turn[]` (unchanged shape/prop name).

**Rendering contract**:
- When the latest turn's `progress` is non-null, renders a chapter numeral
  (`.ovnum.play-chapter-num`, zero-padded, e.g. `03`) and a kicker line reading
  `Chapter {number spelled out} — {locationLabel}`, pinned above the turn list, inside the
  scrolling content (scrolls away with it — not fixed).
- When `progress` is null on the latest turn, renders neither.
- Each turn renders a `.play-label` ("You"/"The story") and a `.play-text` paragraph; a
  player-input row additionally carries `.play-text-player` (italic).
- Scrolls its own container to `scrollHeight` on mount and whenever `turns.length` changes.

## `StatusPanel`

**Props**: `locationLabel`, `goalLabel`, `progress`, `completionReason` (unchanged).

**Rendering contract**:
- `progress` non-null renders a numeral + "of N chapters" plus a segmented bar using the
  shared `.progress-bars` class (research.md Decision 5): one `span` per chapter in
  `progress.total`, the first `progress.current` of them additionally carrying `.filled`.
- Always renders a "Stuck? Get a hint" button (`btn btn-secondary btn-block`) between the
  progress section and the autosave notice. It is **always `disabled`** in this feature and
  carries no click handler; an adjacent `.play-hint-pending` note reads "Hints are coming
  soon." The guidance behind the control is a separate feature (spec.md *Scope note*,
  research.md Decision 2).
- Always renders the autosave notice as its final child (`margin-top: auto`).

## `InstructionInput`

**Props**: unchanged — `{ value, onChange, onSubmit, disabled }`.

**Rendering contract**: unchanged behaviour. The command is submitted exactly as typed;
nothing inspects, flags, or corrects the player's spelling (spec.md Assumptions). Only its
inline styles move to `.play-cmd` / `.play-go` / `.play-visually-hidden`, alongside the
`input` and `btn btn-primary` classes it already carries.

## `TitleBar`

**Rendering contract**: reads `RefreshContext` (`useRefreshContext`), the same context
`NavBar` already reads. When a page has published `{ refresh, loading }`, renders the shared
`RefreshButton` as the first element of the trailing-actions cluster, ahead of "Save a
checkpoint" and "Pause & exit"; when nothing is published, renders none of it (unchanged
default for every non-play screen using `TitleBar`).

## `PlayPage`

**Contract additions**:
- Publishes `{ refresh, loading }` to `RefreshContext` via `usePublishRefresh`, alongside its
  existing `usePublishPlayTitle` publish. `refresh` re-calls `getSession(token, sessionId)`
  and replaces `turns`/`status`/`completionReason` with the response; a failure leaves all
  three untouched, leaves `inputValue` untouched, and surfaces the existing inline notice
  pattern.
- No change to its existing props (`sessionId`, `storyName`, `initialTurns`, `getToken`,
  `onExit`), to its submit path, or to any handler already covered by
  `tests/Play/PlayPage.test.jsx`.

## `AdminStoryTestPlayPage`

Consumes the same `StoryPane`/`StatusPanel`/`InstructionInput`/`SuggestedActions` and the new
shared `Play.css` classes, so `010-story-test-play-done`'s transcript view gets the same
chapter header and progress bar "for free" and does not visually diverge from the real play
surface. It does **not** gain a Refresh control (test-play sessions aren't
resumable/shareable across tabs the way a real session is, and `019-spa-refresh-button`'s
scope never named this screen).
