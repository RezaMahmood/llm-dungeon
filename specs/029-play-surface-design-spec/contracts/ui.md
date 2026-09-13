# UI Contract: Play Surface Design-Spec Conformance

This feature changes no HTTP contract — every endpoint the play surface calls
(`GET /api/game/sessions/{sessionId}`, `POST /api/game/sessions/{sessionId}/interactions`,
`POST /api/game/sessions/{sessionId}/resume`, `POST /api/game/sessions/{sessionId}/checkpoints`)
is unchanged (data-model.md). What changes is the **component contract** between
`PlayPage` and the components it composes, and the markup/class contract each component
presents for styling and testing.

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
- `progress` non-null renders a numeral + "of N chapters" plus a segmented bar: one
  `.play-segment` per chapter in `progress.total`, the first `progress.current` of them
  additionally carrying `.play-segment-done`.
- Always renders a "Stuck? Get a hint" button (`aria-expanded` reflecting open/closed); a
  click toggles a static hint paragraph directly beneath it. No prop controls this — it is
  local component state.
- Always renders the autosave notice as its final child (`margin-top: auto`).

## `InstructionInput`

**Props**: adds one optional prop, `spellingSuggestion?: string`, to the existing
`{ value, onChange, onSubmit, disabled }`.

**Rendering contract**: when `spellingSuggestion` is a non-empty string, renders a
`role="status"` note beneath the command row naming it ("Did you mean **{suggestion}**? …");
otherwise renders nothing there. The prop never disables or blocks `onSubmit`.

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
  three untouched and surfaces the existing inline notice pattern.
- Derives and passes `spellingSuggestion` to `InstructionInput` from the just-completed
  submission (research.md Decision 2); clears it on the next submission regardless of
  outcome.
- No change to its existing props (`sessionId`, `storyName`, `initialTurns`, `getToken`,
  `onExit`) or to any handler already covered by `tests/Play/PlayPage.test.jsx`.

## `AdminStoryTestPlayPage`

Consumes the same `StoryPane`/`StatusPanel`/`InstructionInput`/`SuggestedActions` and the new
shared `Play.css` classes, so `010-story-test-play-done`'s transcript view gets the same
chapter header/progress bar/hint disclosure "for free" and does not visually diverge from the
real play surface. It does **not** gain a Refresh control (test-play sessions aren't
resumable/shareable across tabs the way a real session is, and `019-spa-refresh-button`'s
scope never named this screen).
