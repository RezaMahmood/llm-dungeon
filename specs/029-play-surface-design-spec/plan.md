# Implementation Plan: Play Surface Design-Spec Conformance

**Branch**: `029-play-surface-design-spec` | **Date**: 2026-09-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/029-play-surface-design-spec/spec.md`

## Summary

Bring the existing play surface (`PlayPage`, `StoryPane`, `StatusPanel`,
`InstructionInput`, `SuggestedActions`, `PauseDialog` — delivered by
`008-core-gameplay-done`/`009-save-and-continue`) into full conformance with the
canonical `specs/designs/03-play.html`/`03-play-spec.md` reference named in issue
#332: a chapter numeral/kicker pinned atop the transcript, player-input entries set
in italics, a segmented chapter-progress bar, the "Stuck? Get a hint" control the design
places in the status panel, and a header Refresh control matching
`019-spa-refresh-button`'s existing pattern. The screen's own page-scoped structural rules
move from inline styles into a shared `Play.css` stylesheet, matching how
`028-home-page-redesign` factored `Home.css`. No gameplay, save/resume, checkpoint, or
story-availability behavior changes.

Per spec.md's *Scope note*, the hint control ships inert — `aria-disabled`, still focusable,
so it keeps the focus indicator the constitution's Interaction-states rule requires; the
guidance behind it is a separate feature (research.md Decision 2). Spelling tolerance is not
a requirement of this product and no longer appears anywhere in this feature; the canonical
mockup's spelling-forgiveness hint is a deliberate non-implementation, recorded by T001 as the
second of SC-003's two documented exceptions.

## Technical Context

**Language/Version**: Python 3.12 (backend, Azure Functions), Node.js 22 LTS /
React 19 (frontend) — per constitution Principle III, unchanged by this feature.

**Primary Dependencies**: Frontend only — React, React Router
(`AuthenticatedLayout`/`TitleBar`), axios (`src/frontend/src/services/gameService.js`).
No new dependency, and no backend change: Refresh re-reads the session through the existing
`getSession` call `009-save-and-continue`/`GamePage` already use. No new Cosmos DB field,
endpoint, or LLM-service change.

**Storage**: No change — reads the same `PlaySession`/turn documents
(`STORIES_CONTAINER`/`PLAY_SESSIONS_CONTAINER`) already returned by
`GET /api/game/sessions/{sessionId}` and `POST /api/game/sessions/{sessionId}/interactions`.

**Testing**: `vitest`/React Testing Library (`src/frontend/tests`), the existing
suite for this surface (`tests/Play/*`, `tests/components/TitleBar.test.jsx`,
`tests/components/AdminStoryTestPlayPage.test.jsx`) and the Home suite, which shares the
progress-bar class promoted in research.md Decision 5. No backend test changes are
anticipated since no backend code changes.

**Target Platform**: Browser (React SPA) behind Azure Static Web Apps — unchanged.

**Project Type**: Web application (frontend + backend); this feature touches the
frontend only.

**Performance Goals**: No new goal. The transcript's auto-scroll-to-bottom and
scroll performance at ~1,500 words (spec.md Edge Cases, design spec §8's 10-turn
state) must not regress versus the current implementation.

**Constraints**: Layout/scroll contract (constitution "Layout and scroll contract" #2–3):
only the story pane scrolls; title bar, instruction input, suggested actions, and status
panel stay fixed; the pane auto-scrolls to the newest turn. Design tokens only, from the
app's vendored layer `src/frontend/src/styles/designTokens.css` (source:
`specs/designs/styles.css`) — no literal hex/pixel/font value a token already covers
(constitution "UI Design System Requirements").

**Scale/Scope**: Five existing frontend components restyled/extended
(`StoryPane`, `StatusPanel`, `InstructionInput`, `SuggestedActions`, `PlayPage`),
one existing component extended (`TitleBar`, to surface Refresh), one page reusing
the same components kept in sync (`AdminStoryTestPlayPage`, test-play's own
transcript view), one segmented-bar rule promoted out of `Home.css` into the shared token
layer, one new page-scoped stylesheet (`Play.css`), and the two design artifacts issue #332
attaches vendored into `specs/designs/`. No new screens, no new routes, no new backend
surface.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing** — PASS (planned). Every conformance gap
  closed (chapter header, progress bar, hint control's presence, focusability and
  unavailable state, Refresh control) gets its own test in the existing `tests/Play/*.jsx` /
  `tests/components/TitleBar.test.jsx` suites, alongside the current tests for
  those files, which must keep passing unmodified in what they verify (FR-013). FR-001 and
  SC-002 (the fixed shell, identical across turn counts) get an explicit automated assertion
  rather than manual observation only.
- **II. Secure-by-Default Access** — PASS. No new endpoint or route; the play
  surface remains behind `ProtectedRoute`/`authorize_player` exactly as today.
- **III. Defined Technology Stack** — PASS. No new language, framework, or
  hosting; frontend-only change.
- **IV. Simplicity Over Premature Scale** — PASS. Reuses the existing turn
  payload and `RefreshContext`/`getSession` plumbing `TitleBar`/`NavBar` already
  use elsewhere; no new abstraction layer or state-management pattern.
- **VIII. UI Design System & Accessibility Compliance** — PASS (planned, verified
  at implementation). This feature exists specifically to remove the remaining
  one-off inline styles in favor of the vendored token layer and a small
  page-scoped `Play.css` (constitution "UI Design System Requirements" — "a small
  number of narrowly scoped layout or behavior utility classes" — matching the
  `Home.css` precedent from `028-home-page-redesign`). Inline values are translated to
  tokens, not copied literally (research.md Decision 4); `.play-*` classes are additive, so
  the four interaction states stay in the shared layer; and the segmented progress bar is
  promoted to a shared class rather than forked (research.md Decision 5). This spec's
  FR-005 (suggested actions always alongside free text) is already satisfied
  today and is unchanged here — T003 adds the assertion that guards it through the restyle.
  Readability & interaction rule #1 (narrative prose at or above body size, its line-height or
  greater, `text-wrap: pretty`) is **not** satisfied today: the mockup's prose carries it and
  `StoryPane` does not. T004 closes that gap on `.play-text`.
- **X. PII Protection by Design** — PASS. No new field, no new PII surface.
- **XII. Right-Sized Scope** — PASS. No new infrastructure, no new persistent
  environment; purely conformance work on one existing screen.
- **Layout and scroll contract** — PARTIAL, exception recorded. #2 and #3 are satisfied
  (FR-001/FR-004 restate the existing fixed-shell/auto-scroll rules). **#4 is not**: the play
  surface is a fixed `1fr 292px` grid with no breakpoint, so it is not usable at 320px and
  the status panel does not collapse above the primary content. This is pre-existing from
  `008-core-gameplay-done` and is **not** made worse here; spec.md's Assumptions place
  sub-desktop responsive behavior out of scope, matching the canonical design's own
  exclusion. Recorded here as an explicit, justified exception per Principle VIII rather
  than claimed as a pass, and carried in the PR description as a known limit.
- **Screen contracts** — PASS. The constitution's "Play surface" entry names
  `specs/designs/03-play.html` and `03-play-spec.md` as the acceptance reference and leaves
  this screen's affordances to the specs that own it. The status panel delivers location,
  goal and progress; the hint control ships inert, its behaviour deferred to a separate
  feature (spec.md *Scope note*, research.md Decision 2), which is this spec's own scoping
  decision to make. Supersedes: previously recorded as a deferral against a constitutional
  requirement, withdrawn by constitution v10.0.0 (issue #340).
  `03-play.html`/`03-play-spec.md` are updated in place (issue #332's attachments), not
  replaced with a different canonical screen, so the reference itself is unchanged.

**Complexity Tracking**: the layout-and-scroll exception above is a scope *reduction*
against existing constitution text, not added complexity, so it takes no Complexity
Tracking entry. It is named in the PR description.

**Post-Phase-1 re-check**: Phase 1 introduces no new entity, endpoint, or schema
change (data-model.md below describes only the existing turn shape read
differently on the client). All gates above still hold after design, with the two
exceptions as recorded.

## Project Structure

### Documentation (this feature)

```text
specs/029-play-surface-design-spec/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── ui.md              # Phase 1 output — the play-surface UI contract (no HTTP change)
└── tasks.md               # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
specs/designs/
├── 03-play.html                # updated — issue #332's canonical mockup
├── 03-play-spec.md             # NEW — issue #332's canonical written spec, vendored
└── README.md                   # updated — screen list + implementer notes for 03

src/frontend/
├── src/
│   ├── styles/
│   │   └── designTokens.css     # + shared .progress-bars, promoted out of Home.css
│   │                            #   + .btn[aria-disabled="true"] state selector
│   ├── components/Play/
│   │   ├── Play.css             # NEW — page-scoped structural rules (mirrors Home.css)
│   │   ├── StoryPane.jsx        # + chapter numeral/kicker, italic player entries
│   │   ├── StatusPanel.jsx      # + segmented progress bar, inert hint control
│   │   ├── InstructionInput.jsx # inline styles → Play.css classes
│   │   └── SuggestedActions.jsx # inline styles → Play.css classes
│   ├── components/Home/
│   │   └── Home.css             # .home-pcard-bars reduced to a positioning wrapper
│   ├── components/Layout/
│   │   └── TitleBar.jsx         # + Refresh control (renders RefreshContext's
│   │                            #   published state, matching NavBar's existing pattern)
│   └── pages/
│       ├── PlayPage.jsx         # wires Play.css classes, publishes Refresh
│       └── AdminStoryTestPlayPage.jsx  # same shared components — kept in sync so
│                                #   010-story-test-play-done's transcript view doesn't diverge
└── tests/
    ├── Play/
    │   ├── StoryPane.test.jsx        # + chapter header / italics / auto-scroll tests
    │   ├── StatusPanel.test.jsx      # + progress-bar / inert-hint-control tests
    │   ├── InstructionInput.test.jsx # unchanged behavior; selectors only if affected
    │   ├── PlayPage.test.jsx         # + Refresh integration tests
    │   ├── PlaySurfaceLayout.test.jsx  # + fixed-shell + FR-005 pairing assertions
    │   └── AutosaveDisclosure.test.jsx # selectors only if affected
    └── components/
        ├── Home/HomePage.test.jsx   # regression only — shared .progress-bars
        └── TitleBar.test.jsx        # + Refresh-control tests
```

**Structure Decision**: Existing web-application layout (`src/backend`,
`src/frontend`) is kept as-is; this feature touches only the frontend's existing
`Play` component family, `TitleBar`, and the shared token layer, following the same
page-scoped-stylesheet pattern `028-home-page-redesign` established with `Home.css`. No new
directories.
