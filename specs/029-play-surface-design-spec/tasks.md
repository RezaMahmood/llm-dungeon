---

description: "Task list for play surface design-spec conformance (#332)"
---

# Tasks: Play Surface Design-Spec Conformance

**Input**: Design documents from `/specs/029-play-surface-design-spec/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Canonical UI**: `specs/designs/03-play-spec.md` (written spec, section numbers below refer
to it) and `specs/designs/03-play.html` (mockup) — both are issue #332's attachments, vendored
by T001, and are the acceptance reference for everything a player sees while playing.
**T001 blocks everything**: until `03-play-spec.md` is in the repo, the §-citations below
cannot be checked against anything.

**Scope note** (spec.md): where the design shows a control the app does not implement, this
feature builds the control and defers its behaviour to a separate spec. That applies to the
"Stuck? Get a hint" control only — it ships **disabled** (research.md Decision 2). Spelling
tolerance is not a requirement of this product and appears nowhere in this list.

**Tests**: Included — constitution Principle I (Meaningful, Automated Testing) is
NON-NEGOTIABLE in this repo; every behavior change below ships with a test, and every test
task precedes the implementation it covers.

**Organization**: Grouped by user story (spec.md) so each is independently implementable and
testable. Task IDs are strictly sequential in execution order; `[P]` marks a task whose
prerequisites are met and which shares no file with another `[P]` task in the same group.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup — canonical design reference

**Purpose**: Get issue #332's canonical documents into the repo before any code is written
against them. No application code changes in this phase.

- [ ] T001 Vendor issue #332's attachments into `specs/designs/`: replace `03-play.html` with
  the current canonical mockup as attached, and add `03-play-spec.md` (new file) as the
  written spec. Then update `specs/designs/README.md`: add the `03-play-spec.md` row to the
  screen list, and in "Notes for implementers" record that `03` supersedes its own earlier
  markup and **add a new note** naming any prototype-only affordance the incoming mockup
  carries (e.g. a turn-count state switcher and its `<script>`) as "prototype affordance
  only, must not ship". The README has no such note today — this task writes it, it does not
  cite it.

**Checkpoint**: The canonical design reference is in the repo and `specs/designs/README.md`
agrees with it.

---

## Phase 2: Foundational — shared stylesheet, reading treatment, auto-scroll

**Purpose**: Every user story below assumes (a) the screen's structural rules come from
design-system/page-scoped classes rather than inline styles (constitution "UI Design System
Requirements"; research.md Decision 4), (b) player text reads distinctly from story text
(FR-003), and (c) the transcript auto-scrolls to its newest content (FR-004) — neither (b)
nor (c) exists today (the current `StoryPane` has no scroll-to-bottom logic and no italic
treatment at all).

**⚠️ CRITICAL**: No user story phase can be verified as "independently testable" until this
phase's checkpoint holds, since every story's acceptance scenarios assume a working,
correctly-scrolling transcript.

- [ ] T002 Create `src/frontend/src/components/Play/Play.css` with the page-scoped structural
  classes: `.play-shell`, `.play-body`, `.play-main`, `.play-panel`; `.play-transcript`,
  `.play-entry`, `.play-label`, `.play-text`, `.play-text-player`; `.play-dock`, `.play-try`,
  `.play-chip`, `.play-cmd`, `.play-go`, `.play-notice`, `.play-location`, `.play-goal`,
  `.play-progress-row`, `.play-autosave`, `.play-visually-hidden` — per plan.md's Project
  Structure and contracts/ui.md. **Translate each of today's inline values to the nearest
  token** (`--space-*`, `--font-*`, `--color-*`) from `src/frontend/src/styles/designTokens.css`;
  do **not** copy literal pixel values across (constitution: "a magic pixel value that a token
  already covers is a review blocker"). Carry a value with no token — the 292px panel width,
  the 64ch measure — as a literal with a one-line comment naming it as a deliberate
  exception. Every `.play-*` class is **additive**: controls keep `btn btn-secondary`,
  `input`, `btn btn-primary`, so the four interaction states are never restyled locally
  (research.md Decision 4).
- [ ] T003 [P] Extend `src/frontend/tests/Play/StoryPane.test.jsx`: assert a player-input
  entry carries the italic treatment and a story entry does not (FR-003), and assert the
  scroller's `scrollTop` is driven to `scrollHeight` on mount and after a new turn is
  appended (FR-004). **These must fail before T004.**
- [ ] T004 [P] Add a fixed-shell case to `src/frontend/tests/Play/PlaySurfaceLayout.test.jsx`:
  rendering the play surface with 1, 2, 5 and 10 turns yields the identical header/dock/panel
  structure, and the transcript is the only scroll container (FR-001, SC-002). **Must fail
  before T005–T010 if the shell is wrong.**
- [ ] T005 Rewrite `src/frontend/src/components/Play/StoryPane.jsx` to (a) use the `Play.css`
  classes from T002 instead of inline styles — dropping the dangling `className="storyscroll"`,
  which is defined in no stylesheet in the app — (b) mark player-input entries with
  `.play-text-player` so they read in italics against roman story text (FR-003), and (c) add a
  scroller `ref` + `useEffect` that sets `scrollTop = scrollHeight` on mount and whenever
  `turns.length` changes (FR-004, contracts/ui.md).
- [ ] T006 [P] Update `src/frontend/src/components/Play/SuggestedActions.jsx` to use the
  `Play.css` classes (`.play-try`, `.play-label`, `.play-chip`) **alongside** the existing
  `btn btn-secondary` on each chip — no behavior change, no interaction state restyled.
- [ ] T007 [P] Update `src/frontend/src/components/Play/StatusPanel.jsx` to use the `Play.css`
  classes (`.play-panel`, `.play-label`, `.play-location`, `.play-goal`, `.play-progress-row`,
  `.play-autosave`) for its existing location / goal / progress-numeral / completion-reason /
  autosave rendering — no new affordance yet (the segmented bar lands in Phase 3, the hint
  control in Phase 4).
- [ ] T008 [P] Update `src/frontend/src/components/Play/InstructionInput.jsx` to use the
  `Play.css` classes (`.play-cmd`, `.play-go`, `.play-visually-hidden`) **alongside** the
  existing `input` and `btn btn-primary` classes. No prop change and no behavior change: the
  command is submitted exactly as typed.
- [ ] T009 Update `src/frontend/src/pages/PlayPage.jsx` to import `Play.css` and replace its
  own inline shell/body/main/dock/notice wrapper styles with the `.play-shell`/`.play-body`/
  `.play-main`/`.play-dock`/`.play-notice` classes from T002 — no behavior change.
- [ ] T010 [P] Update `src/frontend/src/pages/AdminStoryTestPlayPage.jsx` the same way as
  T009 (`.play-shell`/`.play-body`/`.play-main`/`.play-dock`/`.play-notice`), keeping
  `010-story-test-play-done`'s transcript view in sync with the real play surface per
  plan.md's Project Structure.
- [ ] T011 Run `npm --prefix src/frontend test -- Play`, `-- TitleBar`, and
  `-- AdminStoryTestPlayPage`, and fix any assertion broken purely by the class-name refactor
  in T002–T010 — no test's *behavior* assertion should need to change, only selectors tied to
  removed inline styles if any exist.

**Checkpoint**: The transcript is built from `Play.css` classes, visually distinguishes
player from story text, and auto-scrolls to the newest turn; the fixed shell is asserted
automatically. Every existing test still passes.

---

## Phase 3: User Story 1 - Track chapter and progress while reading the story (Priority: P1) 🎯 MVP

**Goal**: The transcript shows a chapter numeral/kicker pinned above the turn list, and the
status panel shows a segmented chapter-progress bar — both only when the active story reports
progress, and neither when it doesn't (spec.md FR-002/FR-006).

**Independent Test**: Load a play session with an active story that reports chapter progress
and confirm the transcript shows a chapter identifier at the top of its scrolling content and
the status panel shows a progress indicator with the correct number of segments filled — all
without any additional click (spec.md US1 Acceptance Scenarios 1–3).

### Tests for User Story 1 ⚠️

- [ ] T012 [P] [US1] Add `StoryPane` tests in `src/frontend/tests/Play/StoryPane.test.jsx`:
  the chapter numeral (zero-padded, e.g. `03`) and kicker (`Chapter three — {locationLabel}`)
  render when the latest turn's `progress` is non-null, and neither renders when it is null.
- [ ] T013 [P] [US1] Add `StatusPanel` tests in `src/frontend/tests/Play/StatusPanel.test.jsx`:
  the segmented bar renders exactly `progress.total` segments, with the first
  `progress.current` of them carrying `.filled`, and renders no bar at all when `progress` is
  null.

### Implementation for User Story 1

- [ ] T014 [US1] Promote the segmented-bar rule out of
  `src/frontend/src/components/Home/Home.css` into `src/frontend/src/styles/designTokens.css`
  as shared `.progress-bars` / `.progress-bars span` / `.progress-bars span.filled`
  (research.md Decision 5), leaving `.home-pcard-bars` in `Home.css` as a positioning wrapper
  only, and update `HomePage`/its card component to carry both classes. Principle VIII forbids
  forking a second segmented bar for the play surface.
- [ ] T015 [US1] Extend `src/frontend/src/components/Play/StoryPane.jsx` to render the
  chapter numeral (`.ovnum.play-chapter-num`) and kicker line above the turn list — spelling
  the chapter number as a word ("Chapter three") followed by the same turn's `locationLabel`
  — whenever the latest turn's `progress` is non-null (research.md Decision 1, data-model.md).
- [ ] T016 [US1] Extend `src/frontend/src/components/Play/StatusPanel.jsx` to render the
  shared `.progress-bars` beside the existing numeral + "of N chapters" text, one `span` per
  `progress.total`, the first `progress.current` carrying `.filled`. The numeral text stays —
  meaning is never carried by color alone (constitution, Accessibility).
- [ ] T017 [P] [US1] Add the `Play.css` rules for the classes introduced in T015
  (`.play-chapter-num`, `.play-chapter-line`) to
  `src/frontend/src/components/Play/Play.css`.
- [ ] T018 [US1] Run `npm --prefix src/frontend test -- Home` to confirm T014's promotion
  regressed nothing on the Home page's progress cards.

**Checkpoint**: US1 is independently testable and shippable — a session with progress data
shows the chapter header and segmented bar; a session without shows neither; Home's own
progress cards are unchanged; Phase 2's baseline is unaffected.

---

## Phase 4: User Story 2 - See the play surface the design describes (Priority: P2)

**Goal**: The status panel carries the "Stuck? Get a hint" control in the position and
treatment the canonical design gives it, rendered disabled and honestly labelled, so the panel
matches the design without pretending to offer guidance this feature does not deliver
(spec.md FR-007, *Scope note*).

**Independent Test**: Load the play screen and confirm the control appears between the
progress section and the autosave notice, is disabled, is announced as unavailable, and that
clicking it changes nothing on the screen.

### Tests for User Story 2 ⚠️

- [ ] T019 [P] [US2] Add `StatusPanel` tests in `src/frontend/tests/Play/StatusPanel.test.jsx`:
  a "Stuck? Get a hint" button renders between the progress section and the autosave notice;
  it is `disabled`; the "Hints are coming soon." note renders alongside it; clicking it
  changes nothing rendered. Assert the disabled state through the accessible name/state, not a
  CSS class, so the test survives restyling.

### Implementation for User Story 2

- [ ] T020 [US2] Add the "Stuck? Get a hint" control to
  `src/frontend/src/components/Play/StatusPanel.jsx` — a real `<button type="button">` carrying
  `btn btn-secondary btn-block`, always `disabled`, with no click handler, placed between the
  progress section and the autosave notice per `03-play.html`, followed by a
  `.play-hint-pending` note reading "Hints are coming soon." (research.md Decision 2,
  contracts/ui.md). Do **not** invent hint content or a disclosure behaviour.
- [ ] T021 [P] [US2] Add the `.play-hint` / `.play-hint-pending` rules to
  `src/frontend/src/components/Play/Play.css`. Layout and spacing only — the disabled
  treatment (reduced opacity, `not-allowed` cursor) comes from the shared `.btn:disabled`.

**Checkpoint**: US2 is independently testable and shippable — the status panel matches the
canonical design's composition, and the deferral is visible and honest rather than silent.
The follow-up feature (T027) owns what the control does.

---

## Phase 5: User Story 3 - Recover a stale play screen without leaving the story (Priority: P3)

**Goal**: The header's Refresh control re-syncs the play screen against the session's
currently recorded state, matching `019-spa-refresh-button`'s existing pattern elsewhere
(spec.md FR-009/FR-010).

**Independent Test**: Trigger the header's refresh control and confirm the transcript and
status panel reload from the session's current recorded state while staying on the play
screen; confirm a failed refresh leaves the transcript and typed input intact with a notice.

### Tests for User Story 3 ⚠️

- [ ] T022 [P] [US3] Add `TitleBar` tests in
  `src/frontend/tests/components/TitleBar.test.jsx`: no refresh control renders when nothing
  is published; a published refresh renders `RefreshButton` ahead of "Save a checkpoint"/
  "Pause & exit" in the trailing cluster and invokes it on click; the control is disabled
  while `loading` is true.
- [ ] T023 [P] [US3] Add `PlayPage` tests in `src/frontend/tests/Play/PlayPage.test.jsx`:
  triggering the published refresh calls `getSession(token, sessionId)` and replaces
  `turns`/`status`/`completionReason` with the response; a rejected `getSession` leaves the
  existing transcript **and any typed input** untouched and shows an inline notice.

### Implementation for User Story 3

- [ ] T024 [US3] In `src/frontend/src/pages/PlayPage.jsx`, import `getSession` from
  `../services/gameService.js` (already exported there) and `usePublishRefresh` from
  `../context/RefreshContext.jsx`; implement a `handleRefresh` callback that re-fetches the
  session and replaces `turns`/`status`/`completionReason` on success, or shows the existing
  inline-notice pattern on failure (research.md Decision 3), and publish it via
  `usePublishRefresh({ refresh, loading })`. `inputValue` is never touched by either path.
- [ ] T025 [US3] Update `src/frontend/src/components/Layout/TitleBar.jsx` to read
  `useRefreshContext` (already exported by `RefreshContext.jsx`) and render the shared
  `RefreshButton` as the first element of the trailing-actions cluster whenever a refresh is
  published, matching how `NavBar` already renders it.

**Checkpoint**: US3 is independently testable and shippable — Refresh re-syncs the play
screen; `TitleBar`'s existing checkpoint/pause-and-exit behavior (FR-011) is untouched.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm nothing above regressed existing behavior (spec.md FR-013/SC-005),
file the deferred work, and record manual validation.

- [ ] T026 [P] Review `src/frontend/tests/Play/PlaySurfaceLayout.test.jsx`,
  `src/frontend/tests/Play/AutosaveDisclosure.test.jsx` and
  `src/frontend/tests/Play/InstructionInput.test.jsx` against the Phase 2–5 changes; update
  only selectors incidentally affected by the class refactor — no file's asserted *behavior*
  (exactly one title bar, the pause confirmation gate, the autosave disclosure always
  showing, the command submitted as typed) may change. If the autosave copy is brought into
  line with the mockup ("Saved automatically after every turn."), change it in `StatusPanel`
  and in `AutosaveDisclosure.test.jsx` together, or leave both as they are — do not let them
  diverge.
- [ ] T027 [P] Review `src/frontend/tests/components/AdminStoryTestPlayPage.test.jsx` against
  T010's class refactor — update only incidentally affected selectors, no behavior change.
- [ ] T028 [P] Open the follow-up GitHub issue for the deferred hint action — what a hint
  says, where it comes from, and how the control is enabled — referencing spec.md's *Scope
  note*, plan.md's Screen-contracts exception, and issue #332. Label it `enhancement`. The
  play surface's screen contract is not fully met until that work ships, and nothing should
  rely on anyone remembering that from this task list.
- [ ] T029 Run `npm --prefix src/frontend test`, `npm --prefix src/frontend run lint`, and
  `npm --prefix src/frontend run build` (quickstart.md "Regression check") and fix any
  fallout.
- [ ] T030 Run quickstart.md's manual end-to-end scenario (steps 1–6) against the dev server
  and record the outcome for the PR description's Testing section.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. **Blocks everything**: the
  §-citations throughout this list are uncheckable until `03-play-spec.md` is vendored.
- **Foundational (Phase 2)**: Depends on Phase 1. **BLOCKS all user stories** — every story's
  tests assume a correctly scrolling, class-based transcript.
- **User Stories (Phase 3–5)**: All depend on Phase 2's checkpoint. They touch disjoint files
  (`StoryPane` + `StatusPanel` + `designTokens.css` + `Home.css` for US1; `StatusPanel` for
  US2; `TitleBar` + `PlayPage` for US3) and can proceed in any order; priority order
  (US1 → US2 → US3) matches spec.md.
- **Polish (Phase 6)**: Depends on all three user-story phases being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3.
- **User Story 2 (P2)**: No dependency on US1/US3. Touches `StatusPanel.jsx` alongside US1
  (T016) — see Parallel Opportunities below.
- **User Story 3 (P3)**: No dependency on US1/US2. `PlayPage.jsx` is now touched by this
  story alone.

### Within Each User Story

- Tests MUST be written and FAIL before implementation. This holds in Phase 2 as well: T003
  and T004 precede T005–T010.
- Component changes before the `Play.css` rules that style them (or in parallel, since the
  class names are already fixed by contracts/ui.md).
- Story complete (checkpoint) before moving to Phase 6.

### Parallel Opportunities

- T002 is **not** `[P]`: it creates `Play.css`, which T006–T010 all depend on, and T017/T021
  later append to it.
- Phase 2's `[P]` tasks (T003, T004, T006, T007, T008, T010) touch different files and can run
  in parallel once T002 lands. T005 and T009 are sequential (T005 is the file T003 asserts
  against; T009 imports the stylesheet).
- US1 (T016) and US2 (T020) both edit
  `src/frontend/src/components/Play/StatusPanel.jsx` — **not safe as truly simultaneous
  edits**; do these two sequentially (either order) even though they carry different story
  labels, or have one contributor own both.
- US3 is fully file-disjoint from US1 and US2 and can run in parallel with either.
- Tests for a given story marked `[P]` can run in parallel with each other.

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "StoryPane chapter numeral/kicker tests in src/frontend/tests/Play/StoryPane.test.jsx"
Task: "StatusPanel segmented progress bar tests in src/frontend/tests/Play/StatusPanel.test.jsx"

# Then the shared-class promotion and the two component implementations:
Task: "Promote .progress-bars into src/frontend/src/styles/designTokens.css"
Task: "StoryPane chapter header implementation in src/frontend/src/components/Play/StoryPane.jsx"
Task: "Play.css rules for chapter classes in src/frontend/src/components/Play/Play.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (vendor the canonical design docs).
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1 (chapter/progress).
4. **STOP and VALIDATE**: run quickstart.md steps 1–2, 5 against a session with progress data.
5. Ship if ready — US1 alone already closes the largest visible gap issue #332 names.

### Incremental Delivery

1. Setup + Foundational → transcript reads correctly and scrolls (no visible regression).
2. Add US1 → chapter/progress visible → validate → ship.
3. Add US2 → status panel complete against the design → validate → ship.
4. Add US3 → header Refresh → validate → ship.
5. Phase 6 polish/regression pass, and file the hint follow-up, before the PR closes out
   issue #332.

---

## Notes

- `[P]` tasks = different files, no dependencies (except the two file-overlaps called out
  above: `Play.css` in Phase 2, `StatusPanel.jsx` between US1 and US2).
- `[Story]` label maps task to its spec.md user story for traceability.
- No backend files change anywhere in this task list (plan.md Technical Context) — every
  task above is under `src/frontend/` or `specs/designs/`.
- Verify each story's tests fail before implementing that story.
- Commit after each phase checkpoint.
- Two constitution exceptions are recorded in plan.md and MUST be repeated in the PR
  description: the sub-320px layout gap, and the deferred hint action.
- Avoid: vague tasks, same-file conflicts within a `[P]` batch, cross-story dependencies that
  break independence.
