# Quickstart: Validating Play Surface Design-Spec Conformance

## Prerequisites

- Local offline test harness (`027-local-offline-test-harness`) or the devcontainer with the
  frontend dev server up. No backend change ships with this feature, so no backend fixture
  or emulator setup beyond what gameplay already requires.
- A signed-in player account with at least one active session in a story whose turns report
  `progress` (e.g. the seeded "The Lighthouse at Gullwing Cove" — `src/backend/db/seed_data.py`).

## Frontend validation

```bash
npm --prefix src/frontend test -- Play
npm --prefix src/frontend test -- TitleBar
npm --prefix src/frontend test -- AdminStoryTestPlayPage
npm --prefix src/frontend run lint
npm --prefix src/frontend run build
```

Expected: every existing test in `tests/Play/*`, `tests/components/TitleBar.test.jsx`, and
`tests/components/AdminStoryTestPlayPage.test.jsx` still passes unmodified in what it
verifies (spec.md FR-015/SC-005), plus new passing tests for the chapter header, progress
bar, hint disclosure, spelling-forgiveness note, and header Refresh control (contracts/ui.md).

## Manual end-to-end scenario (dev server)

1. Start a new session in a story that reports chapter progress. **Expect**: the transcript
   opens with a chapter numeral and kicker (e.g. "01 — Chapter one — {location}"); the status
   panel shows the location, goal, and a progress bar with one segment filled.
2. Submit a suggested-action chip, then a free-text move. **Expect**: each of the player's own
   entries renders in italics, the story's replies roman; the transcript stays scrolled to the
   newest reply without the player scrolling.
3. Type a command that closely misspells one of the current suggested actions (e.g. "clim the
   stairs" for "climb the stairs") and submit it. **Expect**: the move is narrated normally, and
   a small note appears under the command line naming the likely intended word; submitting the
   next move clears it.
4. Click "Stuck? Get a hint" in the status panel. **Expect**: guidance appears beneath the
   button in place; clicking again hides it. The transcript and input dock are unaffected.
5. Click the header's Refresh control. **Expect**: the transcript and status panel reload from
   the session's current recorded state while staying on the play screen; type into the
   command field first and confirm it survives a refresh.
6. Reach ten turns of history (~1,500 words). **Expect**: only the transcript pane scrolls;
   the header, input dock, and status panel do not resize or shift (design spec §8).
7. Select "Pause & exit", then "Save and exit to my stories". **Expect**: unchanged from
   today — the confirmation dialog names the current location before any exit (FR-013),
   exactly as `009-save-and-continue`/`008-core-gameplay-done` already require.

## Regression check

```bash
npm --prefix src/frontend test
```

Expected: the full frontend suite passes — this feature must not regress any other screen
that shares `RefreshButton`/`RefreshContext`/`TitleBar` (e.g. `NavBar`'s own Refresh use) or
any existing gameplay/save-and-continue/story-delete test (spec.md FR-015).
