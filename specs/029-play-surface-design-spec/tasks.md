---

description: "Task list for play surface design-spec conformance (#332)"
---

# Tasks: Play Surface Design-Spec Conformance

**Input**: Design documents from `/specs/029-play-surface-design-spec/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Canonical UI**: `specs/designs/03-play-spec.md` (written spec, section numbers below refer
to it) and `specs/designs/03-play.html` (mockup) — both are issue #332's attachments, vendored
by T001, and are the acceptance reference for everything a player sees while playing.

**Tests**: Included — constitution Principle I (Meaningful, Automated Testing) is
NON-NEGOTIABLE in this repo; every behavior change below ships with a test.

**Organization**: Grouped by user story (spec.md) so each is independently implementable and
testable. Task IDs are strictly sequential in execution order; `[P]` marks a task whose
prerequisites are met and which shares no file with another `[P]` task in the same group.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup — canonical design reference

**Purpose**: Get issue #332's canonical documents into the repo before any code is written
against them. No application code changes in this phase.

- [ ] T001 Vendor issue #332's attachments into `specs/designs/`: update `03-play.html` with
  the current canonical mockup (the prototype-only `.statebar` turn-count switcher and its
  `<script>`, italic player entries, `id="scroller"`/`id="transcript"` script-built body —
  kept in the mockup exactly as attached, since `specs/designs/README.md` already documents
  `.statebar` as "prototype affordance only, must not ship"), and add `03-play-spec.md` (new
  file) as the written spec. Update `specs/designs/README.md`'s screen list (add the
  `03-play-spec.md` row) and its "Notes for implementers" section to record that `03`
  supersedes its own earlier markup (research.md) and to flag the `.statebar` exclusion.

**Checkpoint**: The canonical design reference is in the repo and `specs/designs/README.md`
agrees with it.

---

## Phase 2: Foundational — shared stylesheet, reading treatment, auto-scroll

**Purpose**: Every user story below assumes (a) the screen's structural rules come from
design-system/page-scoped classes rather than inline styles (constitution "UI Design System
Requirements"; research.md Decision 5), (b) player text reads distinctly from story text
(FR-003), and (c) the transcript already auto-scrolls to its newest content (FR-004) — none
of which exists today (the current `StoryPane` has no scroll-to-bottom logic and no italic
treatment at all). Doing this first means no user-story phase has to touch it individually.

**⚠️ CRITICAL**: No user story phase can be verified as "independently testable" until this
phase's checkpoint holds, since every story's acceptance scenarios assume a working,
correctly-scrolling transcript.

- [ ] T002 [P] Create `src/frontend/src/components/Play/Play.css` with the page-scoped
  structural classes converting today's inline-style values 1:1 (no visual change yet):
  `.play-shell`, `.play-body`, `.play-main`, `.play-panel`; `.play-transcript`, `.play-entry`,
  `.play-label`, `.play-text`, `.play-text-player`; `.play-dock`, `.play-try`, `.play-chip`,
  `.play-cmd`, `.play-go`, `.play-notice`, `.play-visually-hidden` — per plan.md's Project
  Structure and contracts/ui.md.
- [ ] T003 [P] Rewrite `src/frontend/src/components/Play/StoryPane.jsx` to (a) use the
  `Play.css` classes from T002 instead of inline styles, (b) mark player-input entries with
  `.play-text-player` so they read in italics against roman story text (FR-003), and (c) add
  a scroller `ref` + `useEffect` that sets `scrollTop = scrollHeight` on mount and whenever
  `turns.length` changes (FR-004, contracts/ui.md).
- [ ] T004 [P] Update `src/frontend/src/components/Play/SuggestedActions.jsx` to use the
  `Play.css` classes (`.play-try`, `.play-label`, `.play-chip`) instead of inline styles — no
  behavior change.
- [ ] T005 [P] Update `src/frontend/src/components/Play/StatusPanel.jsx` to use the
  `Play.css` classes (`.play-panel`, `.play-label`, plus new `.play-location`, `.play-goal`,
  `.play-progress-row`, `.play-autosave` added to `Play.css` in this task) for its existing
  location/goal/progress-numeral/autosave rendering — no new affordance yet (the segmented
  bar and hint disclosure land in later phases below).
- [ ] T006 [P] Update `src/frontend/src/components/Play/InstructionInput.jsx` to use the
  `Play.css` classes (`.play-cmd`, `.play-go`, `.play-visually-hidden`) instead of inline
  styles — no new affordance yet (the spelling-forgiveness note lands in Phase 4 below).
- [ ] T007 Update `src/frontend/src/pages/PlayPage.jsx` to import `Play.css` and replace its
  own inline shell/body/main/dock/notice wrapper styles with the `.play-shell`/`.play-body`/
  `.play-main`/`.play-dock`/`.play-notice` classes from T002 — no behavior change.
- [ ] T008 [P] Update `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` the same way as
  T007 (`.play-shell`/`.play-body`/`.play-main`/`.play-dock`/`.play-notice`), keeping
  `010-story-test-play-done`'s transcript view in sync with the real play surface per
  plan.md's Project Structure.
- [ ] T009 [P] Extend `src/frontend/tests/Play/StoryPane.test.jsx`: assert a player-input
  entry carries the italic treatment and a story entry does not (FR-003), and assert the
  scroller's `scrollTop` is driven to `scrollHeight` after a new turn is appended (FR-004).
- [ ] T010 Run `npm --prefix src/frontend test -- Play`, `-- TitleBar`, and
  `-- AdminStoryTestPlayPage`, and fix any assertion broken purely by the class-name refactor
  in T002–T008 — no test's *behavior* assertion should need to change, only selectors tied to
  removed inline styles if any exist.

**Checkpoint**: The transcript is built from `Play.css` classes, visually distinguishes
player from story text, and auto-scrolls to the newest turn — before chapter/progress,
spelling forgiveness, the hint disclosure, or Refresh exist. Every existing test still passes.

---

## Phase 3: User Story 1 - Track chapter and progress while reading the story (Priority: P1) 🎯 MVP

**Goal**: The transcript shows a chapter numeral/kicker pinned above the turn list, and the
status panel shows a segmented chapter-progress bar — both only when the active story reports
progress, and neither when it doesn't (spec.md FR-002/FR-008).

**Independent Test**: Load a play session with an active story that reports chapter progress
and confirm the transcript shows a chapter identifier at the top of its scrolling content and
the status panel shows a progress indicator with the correct number of segments filled — all
without any additional click (spec.md Acceptance Scenarios 1–3).

### Tests for User Story 1 ⚠️

- [ ] T011 [P] [US1] Add `StoryPane` tests in `src/frontend/tests/Play/StoryPane.test.jsx`:
  the chapter numeral (zero-padded, e.g. `03`) and kicker (`Chapter three — {locationLabel}`)
  render when the latest turn's `progress` is non-null, and neither renders when it is null.
- [ ] T012 [P] [US1] Add `StatusPanel` tests in `src/frontend/tests/Play/StatusPanel.test.jsx`:
  the segmented bar renders exactly `progress.total` segments, with the first
  `progress.current` of them carrying the "done" treatment, and renders no bar at all when
  `progress` is null.

### Implementation for User Story 1

- [ ] T013 [US1] Extend `src/frontend/src/components/Play/StoryPane.jsx` to render the
  chapter numeral (`.ovnum.play-chapter-num`) and kicker line above the turn list — spelling
  the chapter number as a word ("Chapter three") followed by the same turn's `locationLabel`
  — whenever the latest turn's `progress` is non-null (research.md Decision 1, data-model.md).
- [ ] T014 [US1] Extend `src/frontend/src/components/Play/StatusPanel.jsx` to render a
  segmented progress bar beside the existing numeral + "of N chapters" text, one segment per
  `progress.total`, the first `progress.current` marked complete.
- [ ] T015 [P] [US1] Add the `Play.css` rules for the classes introduced in T013/T014
  (`.play-chapter-num`, `.play-chapter-line`, `.play-segments`, `.play-segment`,
  `.play-segment-done`) to `src/frontend/src/components/Play/Play.css`.

**Checkpoint**: US1 is independently testable and shippable — a session with progress data
shows the chapter header and segmented bar; a session without shows neither; Phase 2's
baseline (auto-scroll, italics, class-based styling) is unaffected.

---

## Phase 4: User Story 2 - Keep playing despite an imperfect command (Priority: P2)

**Goal**: A likely-misspelled command is still acted on in full, with a small, dismissable
suggestion note appearing beneath the command line (spec.md FR-006/FR-007).

**Independent Test**: Submit a command that closely resembles one of the current turn's
suggested actions but is misspelled, and confirm the move is accepted and narrated normally
while a suggestion note appears; confirm the note clears on the next submission.

### Tests for User Story 2 ⚠️

- [ ] T016 [P] [US2] Add `InstructionInput` tests in
  `src/frontend/tests/Play/InstructionInput.test.jsx`: the suggestion note renders only when
  a `spellingSuggestion` prop is provided, and the input/submit button are never disabled by
  its presence.
- [ ] T017 [P] [US2] Add `PlayPage` tests in `src/frontend/tests/Play/PlayPage.test.jsx`: a
  submission that closely misses one of the resulting turn's `suggestedActions` still calls
  `submitInteraction` with the player's text exactly as typed and shows a suggestion note; the
  note clears after the next submission regardless of that submission's own outcome.

### Implementation for User Story 2

- [ ] T018 [US2] Add a `spellingSuggestion` prop to
  `src/frontend/src/components/Play/InstructionInput.jsx` rendering the non-blocking
  `role="status"` note under the command row per contracts/ui.md ("Did you mean
  **{suggestion}**? Press Go again and I'll take it either way.").
- [ ] T019 [US2] Implement the client-side near-miss comparison (research.md Decision 2) in
  `src/frontend/src/pages/PlayPage.jsx`: after a successful submit, compare the player's
  submitted text against the new turn's `suggestedActions`; set `spellingSuggestion` to the
  closest near-miss (or clear it) and pass it through to `InstructionInput`.
- [ ] T020 [P] [US2] Add the `.play-spelling` rule to
  `src/frontend/src/components/Play/Play.css`.

**Checkpoint**: US2 is independently testable and shippable — spelling forgiveness works
without touching US1's chapter header/progress bar.

---

## Phase 5: User Story 3 - Get unstuck without losing your place (Priority: P2)

**Goal**: "Stuck? Get a hint" in the status panel reveals guidance in place and can be
dismissed, without leaving the play screen or disturbing the transcript (spec.md FR-009).

**Independent Test**: Click "Stuck? Get a hint" and confirm guidance appears within the
status panel with the transcript and input dock unaffected; click again and confirm it hides.

### Tests for User Story 3 ⚠️

- [ ] T021 [P] [US3] Add `StatusPanel` tests in `src/frontend/tests/Play/StatusPanel.test.jsx`:
  clicking "Stuck? Get a hint" reveals hint text and sets `aria-expanded="true"`; clicking
  again hides it and resets `aria-expanded` to `"false"`.

### Implementation for User Story 3

- [ ] T022 [US3] Add local open/closed disclosure state and generic, non-story-specific hint
  copy to the existing "Stuck? Get a hint" button in
  `src/frontend/src/components/Play/StatusPanel.jsx` (research.md Decision 3).
- [ ] T023 [P] [US3] Add the `.play-hint`/`.play-hint-body` rules to
  `src/frontend/src/components/Play/Play.css`.

**Checkpoint**: US3 is independently testable and shippable — the hint discloses/hides in
place; US1's and US2's behavior is untouched.

---

## Phase 6: User Story 4 - Recover a stale play screen without leaving the story (Priority: P3)

**Goal**: The header's Refresh control re-syncs the play screen against the session's
currently recorded state, matching `019-spa-refresh-button`'s existing pattern elsewhere
(spec.md FR-011/FR-012).

**Independent Test**: Trigger the header's refresh control and confirm the transcript and
status panel reload from the session's current recorded state while staying on the play
screen; confirm a failed refresh leaves the transcript and typed input intact with a notice.

### Tests for User Story 4 ⚠️

- [ ] T024 [P] [US4] Add `TitleBar` tests in
  `src/frontend/tests/components/TitleBar.test.jsx`: no refresh control renders when nothing
  is published; a published refresh renders `RefreshButton` ahead of "Save a checkpoint"/
  "Pause & exit" in the trailing cluster and invokes it on click; the control is disabled
  while `loading` is true.
- [ ] T025 [P] [US4] Add `PlayPage` tests in `src/frontend/tests/Play/PlayPage.test.jsx`:
  triggering the published refresh calls `getSession(token, sessionId)` and replaces
  `turns`/`status`/`completionReason` with the response; a rejected `getSession` leaves the
  existing transcript and any typed input untouched and shows an inline notice.

### Implementation for User Story 4

- [ ] T026 [US4] In `src/frontend/src/pages/PlayPage.jsx`, import `getSession` from
  `../services/gameService.js` (already exported there) and `usePublishRefresh` from
  `../context/RefreshContext.jsx`; implement a `handleRefresh` callback that re-fetches the
  session and replaces `turns`/`status`/`completionReason` on success, or shows the existing
  inline-notice pattern on failure (research.md Decision 4), and publish it via
  `usePublishRefresh({ refresh, loading })`.
- [ ] T027 [US4] Update `src/frontend/src/components/Layout/TitleBar.jsx` to read
  `useRefreshContext` (already exported by `RefreshContext.jsx`) and render the shared
  `RefreshButton` as the first element of the trailing-actions cluster whenever a refresh is
  published, matching how `NavBar` already renders it.

**Checkpoint**: US4 is independently testable and shippable — Refresh re-syncs the play
screen; `TitleBar`'s existing checkpoint/pause-and-exit behavior (FR-013) is untouched.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Confirm nothing above regressed existing behavior (spec.md FR-015/SC-005), and
record manual validation.

- [ ] T028 [P] Review `src/frontend/tests/Play/PlaySurfaceLayout.test.jsx` and
  `src/frontend/tests/Play/AutosaveDisclosure.test.jsx` against the Phase 2–6 changes; update
  only selectors/copy incidentally affected by the class refactor — neither file's asserted
  *behavior* (exactly one title bar, the pause confirmation gate, the autosave disclosure
  always showing) may change.
- [ ] T029 [P] Review `src/frontend/tests/components/AdminStoryTestPlayPage.test.jsx` against
  T008's class refactor — update only incidentally affected selectors, no behavior change.
- [ ] T030 Run `npm --prefix src/frontend test`, `npm --prefix src/frontend run lint`, and
  `npm --prefix src/frontend run build` (quickstart.md "Regression check") and fix any
  fallout.
- [ ] T031 Run quickstart.md's manual end-to-end scenario (steps 1–7) against the dev server
  and record the outcome for the PR description's Testing section.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 (T001's vendored spec informs T002's class
  names). **BLOCKS all user stories** — every story's tests assume a correctly scrolling,
  class-based transcript.
- **User Stories (Phase 3–6)**: All depend on Phase 2's checkpoint. They touch disjoint files
  (`StoryPane`+`Play.css` for US1; `InstructionInput`+`PlayPage`+`Play.css` for US2;
  `StatusPanel`+`Play.css` for US3; `TitleBar`+`PlayPage` for US4) and can proceed in any
  order or in parallel; priority order (US1 → US2 → US3 → US4) matches spec.md.
- **Polish (Phase 7)**: Depends on all four user-story phases being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3/US4.
- **User Story 2 (P2)**: No dependency on US1/US3/US4 (touches `PlayPage.jsx` alongside
  US4 — see Parallel Example below for the file-overlap note).
- **User Story 3 (P2)**: No dependency on US1/US2/US4.
- **User Story 4 (P3)**: No dependency on US1/US2/US3 (also touches `PlayPage.jsx` — see
  below).

### Within Each User Story

- Tests MUST be written and FAIL before implementation.
- Component changes before the `Play.css` rules that style them (or in parallel, since the
  class names are already fixed by contracts/ui.md).
- Story complete (checkpoint) before moving to Phase 7.

### Parallel Opportunities

- All Phase 2 tasks marked `[P]` (T002–T006, T008, T009) touch different files and can run
  in parallel once T001 lands.
- US1, US3 are fully file-disjoint from each other and from US2/US4, and can be implemented
  in parallel.
- US2 (T019) and US4 (T026) both edit `src/frontend/src/pages/PlayPage.jsx` — **not safe to
  run as truly simultaneous edits**; do these two sequentially (either order) even though
  they carry different story labels, or have one contributor own both.
- Tests for a given story marked `[P]` can run in parallel with each other.

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "StoryPane chapter numeral/kicker tests in src/frontend/tests/Play/StoryPane.test.jsx"
Task: "StatusPanel segmented progress bar tests in src/frontend/tests/Play/StatusPanel.test.jsx"

# Then the CSS addition can proceed alongside the two component implementations:
Task: "StoryPane chapter header implementation in src/frontend/src/components/Play/StoryPane.jsx"
Task: "StatusPanel progress bar implementation in src/frontend/src/components/Play/StatusPanel.jsx"
Task: "Play.css rules for chapter/progress classes in src/frontend/src/components/Play/Play.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (vendor the canonical design docs).
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1 (chapter/progress).
4. **STOP and VALIDATE**: run quickstart.md steps 1–2, 6 against a session with progress data.
5. Ship if ready — US1 alone already closes the largest visible gap issue #332 names.

### Incremental Delivery

1. Setup + Foundational → transcript reads correctly and scrolls (no visible regression).
2. Add US1 → chapter/progress visible → validate → ship.
3. Add US2 → spelling forgiveness → validate → ship.
4. Add US3 → hint disclosure → validate → ship.
5. Add US4 → header Refresh → validate → ship.
6. Phase 7 polish/regression pass before the PR closes out issue #332.

---

## Notes

- `[P]` tasks = different files, no dependencies (except the one file-overlap called out
  above between US2 and US4 on `PlayPage.jsx`).
- `[Story]` label maps task to its spec.md user story for traceability.
- No backend files change anywhere in this task list (plan.md Technical Context) — every
  task above is under `src/frontend/` or `specs/designs/`.
- Verify each story's tests fail before implementing that story.
- Commit after each phase checkpoint.
- Avoid: vague tasks, same-file conflicts within a `[P]` batch, cross-story dependencies that
  break independence.
