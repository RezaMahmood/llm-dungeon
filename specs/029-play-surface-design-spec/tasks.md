---
description: "Task list for play surface design-spec conformance (#332)"
---

# Tasks: Play Surface Design-Spec Conformance

**Input**: `/specs/029-play-surface-design-spec/` — spec.md, plan.md, research.md,
data-model.md, contracts/ui.md, quickstart.md.

**Canonical UI**: `specs/designs/03-play-spec.md` (written spec) and
`specs/designs/03-play.html` (mockup), vendored by T001. Together they are the acceptance
reference for everything a player sees while playing.

## Binding decisions

Referenced by number below rather than restated in each task.

- **D1 — Canonical reference.** T001 vendors it; nothing else here can be checked against the
  design until it lands.
- **D2 — The hint control ships inert.** `aria-disabled="true"`, never the native `disabled`
  attribute, so it stays in the tab order and keeps its focus ring (spec.md US2 AS2;
  constitution, Interaction states). No hint content and no disclosure behaviour is invented
  here (spec.md *Scope note*; research.md Decision 2).
- **D3 — Styling.** `.play-*` classes are additive layout-only modifiers; every control keeps
  its design-system class (`btn btn-secondary`, `input`, `btn btn-primary`). Interaction-state
  styling lives only in `designTokens.css`, never in `Play.css`. Inline values are translated
  to the nearest `--space-*`/`--font-*`/`--color-*` token, not copied as literals; the only
  two literals permitted are the 292px panel width and the 64ch measure, each carrying a
  comment naming it as a deliberate exception (research.md Decision 4).
- **D4 — No spelling tolerance.** The mockup's spelling-forgiveness hint is deliberately not
  implemented (spec.md Assumptions).
- **D5 — One segmented bar.** The progress bar is promoted to a shared class and consumed by
  both Home and the play surface; forking a second is forbidden (research.md Decision 5).
- **D6 — Frontend only.** No backend file changes. Every path below is under `src/frontend/`
  or `specs/designs/`, and `src/` and `tests/` are relative to `src/frontend/`.
- **D7 — SC-003 allows exactly two exceptions.** The hint control's guidance (D2) and the
  spelling-forgiveness hint (D4). Any third gap found in T031 is a finding, not an exception.

## Conventions

- IDs run in execution order. `[P]` marks a task that may run alongside other `[P]` tasks in
  the same phase; the **File ownership** table is the authority on what may overlap.
- `[US1]`/`[US2]`/`[US3]` map a task to its spec.md user story.
- Tests precede the implementation they cover and MUST fail first (constitution Principle I).
- Commit at each checkpoint.

---

## Phase 1: Setup — canonical design reference

- [X] **T001** Vendor issue #332's attachments into `specs/designs/`: replace `03-play.html`
  with the attached mockup and add `03-play-spec.md`. Update `specs/designs/README.md` — add
  the `03-play-spec.md` row to the screen list, record that `03` supersedes its own earlier
  markup, and add a new note (there is none today) naming both (a) any prototype-only
  affordance the incoming mockup carries, such as a turn-count state switcher and its
  `<script>`, as "prototype affordance only, must not ship", and (b) the spelling-forgiveness
  hint as a deliberate non-implementation per D4.

**Checkpoint**: the canonical reference is in the repo and the README agrees with it.

---

## Phase 2: Foundational — stylesheet, reading treatment, auto-scroll

Nothing in Phases 3–5 is independently testable until this checkpoint holds: every story's
acceptance scenarios assume a class-based, correctly scrolling transcript. Neither the italic
player treatment nor the auto-scroll exists today.

- [X] **T002** [P] `tests/Play/StoryPane.test.jsx` — assert a player-input entry carries the
  italic treatment and a story entry does not (FR-003); assert the scroller's `scrollTop` is
  driven to `scrollHeight` on mount and after a turn is appended (FR-004). Must fail before
  T005.
- [X] **T003** [P] `tests/Play/PlaySurfaceLayout.test.jsx` — assert the header, dock and panel
  are structurally identical at 1, 2, 5 and 10 turns, and that the transcript is the only
  scroll container (FR-001, SC-002); assert the suggested-action chips and the free-text
  command field render together for a session still accepting moves, never one in place of the
  other (FR-005). Must fail before T004–T010 if either is wrong.
- [X] **T004** Create `src/components/Play/Play.css` with the page-scoped classes named in
  contracts/ui.md: `.play-shell`, `.play-body`, `.play-main`, `.play-panel`,
  `.play-transcript`, `.play-entry`, `.play-label`, `.play-text`, `.play-text-player`,
  `.play-dock`, `.play-try`, `.play-chip`, `.play-cmd`, `.play-go`, `.play-notice`,
  `.play-location`, `.play-goal`, `.play-progress-row`, `.play-autosave`,
  `.play-visually-hidden`. Per D3. Two rules the screen lacks entirely today and must gain
  here:
  - `.storyscroll` — the mockup's scrollbar treatment (`03-play.html:14-15`). The class is on
    `StoryPane` today but no stylesheet defines it, and `specs/designs/README.md` both names
    it the play surface's scroll container and sanctions it as a permitted utility.
  - `.play-text` — the constitution's Readability rule #1 for narrative prose: at or above the
    design system's body size, its line-height or greater, and `text-wrap: pretty`, as the
    mockup's own prose paragraphs have it (`03-play.html:46`).
- [X] **T005** `src/components/Play/StoryPane.jsx` — replace inline styles with the T004
  classes, keeping `className="storyscroll"`; mark player-input entries `.play-text-player`
  (FR-003); add a scroller `ref` and a `useEffect` setting `scrollTop = scrollHeight` on mount
  and whenever `turns.length` changes (FR-004).
- [X] **T006** [P] `src/components/Play/SuggestedActions.jsx` — apply `.play-try`,
  `.play-label`, `.play-chip`. No behaviour change.
- [X] **T007** [P] `src/components/Play/InstructionInput.jsx` — apply `.play-cmd`, `.play-go`,
  `.play-visually-hidden`. No prop or behaviour change; the command is still submitted exactly
  as typed.
- [X] **T008** [P] `src/components/Play/StatusPanel.jsx` — apply `.play-panel`, `.play-label`,
  `.play-location`, `.play-goal`, `.play-progress-row`, `.play-autosave` to the existing
  location / goal / progress-numeral / completion-reason / autosave rendering. No new
  affordance: the segmented bar is T017, the hint control T020.
- [X] **T009** `src/pages/PlayPage.jsx` — import `Play.css`; replace the inline
  shell/body/main/dock/notice wrappers with `.play-shell`, `.play-body`, `.play-main`,
  `.play-dock`, `.play-notice`. No behaviour change.
- [X] **T010** [P] `src/pages/AdminStoryTestPlayPage.jsx` — same wrapper classes as T009, so
  `010-story-test-play-done`'s transcript view stays in sync with the real play surface.
- [X] **T011** Run `npm --prefix src/frontend test -- Play`, `-- TitleBar`,
  `-- AdminStoryTestPlayPage`. Fix only selectors tied to removed inline styles; no existing
  test's asserted behaviour may change.

**Checkpoint**: the transcript is class-based, distinguishes player from story text, and
auto-scrolls; the fixed shell and the chips/command-line pairing are asserted; every existing
test passes.

---

## Phase 3: User Story 1 — chapter and progress while reading (P1) 🎯 MVP

**Goal**: the transcript shows a chapter numeral and kicker above the turn list, and the status
panel a segmented progress bar — both only when the active story reports progress, neither when
it does not (FR-002, FR-006).

**Independent test**: load a session reporting chapter progress; confirm both appear with the
correct segment count, and that a session without progress data shows neither (US1 AS1–3).

- [ ] **T012** [P] [US1] `tests/Play/StoryPane.test.jsx` — the zero-padded numeral (e.g. `03`)
  and the kicker `Chapter three — {locationLabel}` render when the latest turn's `progress` is
  non-null; neither renders when it is null.
- [ ] **T013** [P] [US1] `tests/Play/StatusPanel.test.jsx` — the bar renders exactly
  `progress.total` segments with the first `progress.current` carrying `.filled`, and no bar
  at all when `progress` is null.
- [ ] **T014** [US1] Promote the segmented-bar rule from `src/components/Home/Home.css` into
  `src/styles/designTokens.css` as `.progress-bars`, `.progress-bars span` and
  `.progress-bars span.filled` (D5). Reduce `.home-pcard-bars` to a positioning wrapper and
  have `HomePage`'s card carry both classes.
- [ ] **T015** [US1] `src/components/Play/StoryPane.jsx` — render the chapter numeral
  (`.ovnum.play-chapter-num`) and the kicker line above the turn list, spelling the number as a
  word followed by that turn's `locationLabel`, whenever the latest turn's `progress` is
  non-null (research.md Decision 1).
- [ ] **T016** [US1] `src/components/Play/Play.css` — add `.play-chapter-num` and
  `.play-chapter-line`.
- [ ] **T017** [US1] `src/components/Play/StatusPanel.jsx` — render the shared `.progress-bars`
  beside the existing numeral and "of N chapters" text, one `span` per `progress.total`, the
  first `progress.current` carrying `.filled`. The numeral text stays: meaning is never carried
  by colour alone.
- [ ] **T018** [US1] Run `npm --prefix src/frontend test -- Home` — T014 must have regressed
  nothing on the Home page's progress cards.

**Checkpoint**: US1 ships independently. A session with progress shows the chapter header and
bar; one without shows neither; Home is unchanged.

---

## Phase 4: User Story 2 — the status panel the design describes (P2)

**Goal**: the status panel carries the "Stuck? Get a hint" control in the position and treatment
the canonical design gives it, inert and honestly labelled (FR-007, D2).

**Independent test**: the control appears between the progress section and the autosave notice,
keyboard focus reaches it and shows the accent focus ring, a screen reader announces it as
unavailable, and clicking it changes nothing.

- [ ] **T019** [US2] `tests/Play/StatusPanel.test.jsx` — a "Stuck? Get a hint" button renders
  between the progress section and the autosave notice; it carries `aria-disabled="true"`; the
  native `disabled` attribute is absent and the element stays keyboard-reachable; the "Hints
  are coming soon." note renders alongside; clicking changes nothing rendered. Assert state
  through the accessible name/state, not a CSS class. A test that accepts `disabled` would pass
  against an implementation that fails US2 AS2.
- [ ] **T020** [US2] `src/components/Play/StatusPanel.jsx` — add a `<button type="button">`
  carrying `btn btn-secondary btn-block` and `aria-disabled="true"`, with no click handler,
  between the progress section and the autosave notice per `03-play.html:91`, followed by a
  `.play-hint-pending` note reading "Hints are coming soon." Per D2.
- [ ] **T021** [US2] `src/styles/designTokens.css` — widen the existing rule at line 132 to
  `.btn:disabled, .btn[aria-disabled="true"]`, so the unavailable treatment reaches an
  `aria-disabled` control. Per D3 this belongs in the shared layer, not `Play.css`.
- [ ] **T022** [US2] `src/components/Play/Play.css` — add `.play-hint` and
  `.play-hint-pending`. Layout and spacing only.

**Checkpoint**: US2 ships independently. The panel matches the canonical composition and the
deferral is visible rather than silent; T033 files what the control will eventually do.

---

## Phase 5: User Story 3 — recover a stale play screen (P3)

**Goal**: the header's Refresh control re-syncs the play screen against the session's recorded
state, reusing `019-spa-refresh-button`'s existing pattern (FR-009, FR-010).

**Independent test**: trigger the header refresh and confirm the transcript and status panel
reload while staying on the play screen; confirm a failed refresh keeps the transcript and any
typed input, with a notice.

- [ ] **T023** [P] [US3] `tests/components/TitleBar.test.jsx` — no refresh control renders when
  nothing is published; a published refresh renders `RefreshButton` ahead of "Save a
  checkpoint" and "Pause & exit" and invokes it on click; the control is disabled while
  `loading` is true.
- [ ] **T024** [P] [US3] `tests/Play/PlayPage.test.jsx` — the published refresh calls
  `getSession(token, sessionId)` and replaces `turns`/`status`/`completionReason`; a rejected
  `getSession` leaves the transcript and any typed input untouched and shows an inline notice.
- [ ] **T025** [US3] `src/pages/PlayPage.jsx` — import `getSession` from
  `../services/gameService.js` and `usePublishRefresh` from `../context/RefreshContext.jsx`
  (both already exported). Add a `handleRefresh` that re-fetches the session and replaces
  `turns`/`status`/`completionReason` on success, or surfaces the existing inline notice on
  failure; publish it as `usePublishRefresh({ refresh, loading })`. Neither path touches
  `inputValue`.
- [ ] **T026** [US3] `src/components/Layout/TitleBar.jsx` — read `useRefreshContext` and render
  the shared `RefreshButton` as the first element of the trailing-actions cluster whenever a
  refresh is published, as `NavBar` already does.

**Checkpoint**: US3 ships independently. Refresh re-syncs the screen; the existing
checkpoint/pause-and-exit behaviour (FR-011) is untouched.

---

## Phase 6: Regression, conformance, handoff

- [ ] **T027** [P] Align the autosave copy with the mockup: `StatusPanel` reads "Autosaved after
  every turn" today, `03-play.html:92` reads "Saved automatically after every turn." SC-003
  requires the mockup's wording, so change `src/components/Play/StatusPanel.jsx` and
  `tests/Play/AutosaveDisclosure.test.jsx` together, and update any selector in that test file
  affected by the class refactor. The disclosure stays present at all times (FR-008); only the
  wording moves.
- [ ] **T028** [P] Review `tests/Play/PlaySurfaceLayout.test.jsx` and
  `tests/Play/InstructionInput.test.jsx` against Phases 2–5. Update only selectors affected by
  the class refactor; the asserted behaviour — exactly one title bar, the pause confirmation
  gate, the command submitted as typed — may not change.
- [ ] **T029** [P] `tests/components/AdminStoryTestPlayPage.test.jsx` — update selectors
  affected by T010, then add an assertion that the inherited affordances actually render: for a
  test-play turn carrying `progress`, the chapter header and the segmented bar appear, as
  contracts/ui.md promises. Without it that page can silently diverge from the play surface.
- [ ] **T030** Run `npm --prefix src/frontend test`, `npm --prefix src/frontend run lint` and
  `npm --prefix src/frontend run build`. All three green (FR-013, SC-005).
- [ ] **T031** Discharge **SC-003**: walk `specs/designs/03-play-spec.md` section by section and
  `03-play.html` element by element against the built screen, recording each element as present
  in the position the design gives it. Exactly two exceptions may be recorded, per D7; any third
  gap is fixed or raised before the PR. Nothing else in this list discharges SC-003 — T032's
  scenario walks flows, not elements. Carry the outcome into the PR description.
- [ ] **T032** Run quickstart.md's manual scenario (steps 1–6) against the dev server and record
  the outcome for the PR description's Testing section.
- [ ] **T033** Open the follow-up GitHub issue for the deferred hint action — what a hint says,
  where it comes from, and how the control is enabled — referencing spec.md's *Scope note*,
  plan.md's Screen-contracts exception, and issue #332. Label it `enhancement`. The screen
  contract is not met until that work ships, and nothing should depend on someone remembering
  it.

---

## Dependencies

### Phases

| Phase | Depends on | Note |
|---|---|---|
| 1 Setup | — | Blocks everything (D1) |
| 2 Foundational | 1 | **Blocks all three stories** |
| 3 US1 (P1) | 2 | |
| 4 US2 (P2) | 2 | |
| 5 US3 (P3) | 2 | File-disjoint from US1 and US2 |
| 6 Regression | 3, 4, 5 | |

Phases 3–5 do not depend on each other and may run in any order; US1 → US2 → US3 matches
spec.md's priorities.

### File ownership

Every file touched more than once, with the only valid order. Two tasks in the same row never
run in parallel, whatever their `[P]` marks or story labels say.

| File | Order |
|---|---|
| `src/components/Play/StatusPanel.jsx` | T008 → T017 → T020 → T027 |
| `src/components/Play/Play.css` | T004 → T016 → T022 |
| `src/components/Play/StoryPane.jsx` | T005 → T015 |
| `src/styles/designTokens.css` | T014 → T021 |
| `src/pages/PlayPage.jsx` | T009 → T025 |
| `tests/Play/StoryPane.test.jsx` | T002 → T012 |
| `tests/Play/StatusPanel.test.jsx` | T013 → T019 |
| `tests/Play/PlaySurfaceLayout.test.jsx` | T003 → T028 |

`StatusPanel.jsx` spans three phases. If the stories are split between contributors, one owner
takes all four of its tasks.

---

## Delivery

1. **T001–T011** — the surface is class-based, reads correctly and scrolls. Nothing visibly new
   to a player yet.
2. **T012–T018 (MVP)** — chapter and progress visible. Validate with quickstart steps 1, 2 and
   5; shippable alone, and it closes the largest gap issue #332 names.
3. **T019–T022** — the status panel is complete against the design.
4. **T023–T026** — header Refresh.
5. **T027–T033** — regression, the SC-003 conformance sweep, and the follow-up issue, before
   the PR closes out #332.

The PR description must repeat plan.md's two constitution exceptions: the sub-320px layout gap,
and the deferred hint action.
