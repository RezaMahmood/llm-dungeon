---
description: "Task list for the Sessions (admin) screen and session deletion (#335)"
---

# Tasks: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Input**: `/specs/031-sessions-admin-design-spec/` — spec.md, plan.md, research.md,
data-model.md, contracts/api.md, contracts/ui.md, quickstart.md.

**Canonical UI**: `specs/designs/08-admin-sessions-spec.md` (written spec) and
`specs/designs/08-admin-sessions.html` (mockup), vendored by T001. Where the two disagree with
each other, the written spec wins; where either disagrees with the constitution, the
constitution wins.

## Binding decisions

Referenced by number below rather than restated in each task.

- **D1 — Canonical reference.** Vendored by T001. Nothing here can be checked against the
  design until it lands.
- **D2 — Governance gate.** The constitution's **Administrator — sessions** screen contract
  says "no prototype screen" and "a read-only list". This feature contradicts both, so T002
  amends it. The screen MUST NOT ship ahead of that amendment (spec FR-021, research.md
  Decision 10).
- **D3 — One delete endpoint, no client-supplied kind.** `DELETE
  /api/manage/sessions/{sessionId}` resolves player vs test-play server-side from the id alone
  (research.md Decision 1). `sessionType` is never sent back.
- **D4 — Admin deletes are separate, explicitly named methods.** `delete_session_as_administrator`
  on each session service. The existing owner-checked methods are NOT given an optional-owner
  mode (research.md Decision 2).
- **D5 — `session_removed` is its own outcome.** Split from `story_deleted`, which stays
  exactly as it is for a genuinely deleted story (spec FR-012a, research.md Decision 3,
  contracts/api.md).
- **D6 — The message names no actor.** "This session has been removed. You can start this story
  again from your home page." The server cannot tell an admin's delete from the player's own in
  another tab (research.md Decision 4).
- **D7 — The bump is a navigation.** Play surface → `GamePage` → `navigate("/menu")` → a
  dismissible dialog on Home, not an in-place notice with a button (research.md Decision 5).
- **D8 — Reuse, don't reimplement.** `ConfirmDeleteDialog` for the confirmation,
  `RefreshContext` for refresh, `designTokens.css`'s shared button language for every button
  state. `AdminSessions.css` carries page structure only (research.md Decisions 6, 7).
- **D9 — Two documented deviations from the mockup, and no more.** The dialog's buttons sit in
  a row rather than stacked (D8), and the table caption is reworded because the mockup's "usage
  record" does not exist (spec *Scope note: honest data*). A third gap found in T037 is a
  finding, not an exception.
- **D10 — PII.** The confirm dialog quotes the owning account. That string stays in the
  rendered, access-controlled UI: never in a log, a trace, a test fixture using a real address,
  a commit message, or the PR description (Principle X).

## Conventions

- IDs run in execution order. `[P]` marks a task that may run alongside other `[P]` tasks in
  the same phase; different files, no dependency on an incomplete task.
- `[US1]`–`[US4]` map a task to its spec.md user story.
- Tests precede the implementation they cover and MUST fail first (constitution Principle I).
- Paths are relative to the repo root; `src/`/`tests/` under `src/frontend/` unless prefixed
  `src/backend/`.
- Commit at each checkpoint.

---

## Phase 1: Setup — canonical reference

- [X] **T001** Vendor issue #335's attachments into `specs/designs/`:
  `08-admin-sessions.html` and `08-admin-sessions-spec.md`, and add both to
  `specs/designs/README.md`'s screen list with an implementer note recording that this screen
  had no prototype before, that Delete supersedes `026-token-usage` FR-016, and the caption
  deviation (D9). *(Done in this session — verify it matches the final vendored files.)*

---

## Phase 2: Foundational (governance gate)

**⚠️ CRITICAL**: D2. The screen is untraceable to a screen contract until T002 lands.

- [X] **T002** Amend `.specify/memory/constitution.md`'s **Administrator — sessions** screen
  contract: name `specs/designs/08-admin-sessions.html` and `08-admin-sessions-spec.md` as its
  acceptance reference, replace "read-only list" with the list plus an administrator delete
  behind a confirmation dialog, and drop the "no prototype screen"/"defers this screen's visual
  design" clauses. Bump the version MINOR (9.0.0 → 9.1.0), update **Last Amended**, and replace
  the Sync Impact Report with this amendment's (Principle XIV: the report carries only the
  current amendment).
- [X] **T003** Record the supersession in `specs/026-token-usage/spec.md`: mark FR-016 as
  superseded by `031-sessions-admin-design-spec` FR-006 in one line, edited in place — no
  retained narrative of the old decision (Principle XIV).

**Checkpoint**: the screen contract now permits what the rest of this feature builds.

---

## Phase 3: User Story 1 — Review every session at a glance (P1) 🎯 MVP

**Goal**: The Sessions screen matches the canonical design as a read-only surface — shell,
kicker, computed heading, table, empty state.

**Independent Test**: Load the screen with player and test-play rows, zero-token and
high-token, live and deleted stories, and read every value off the table; then empty the list
and see the empty state. No delete involved.

### Tests for User Story 1

- [X] **T004** [P] [US1] Write `tests/components/SessionsTable.test.jsx` covering: the five
  columns in order; `(deleted story)` rendered as an italic label, not an empty cell; a token
  total of `0` rendering as `0`; a four-figure total thousands-separated; a full UUID present
  and wrapping (no truncation); the account rendered muted.
- [X] **T005** [P] [US1] Extend `tests/integration/admin_sessions_list.test.jsx` for the
  heading: `{n} sessions across {m} stories`, `1 session across 1 story` singularising both
  halves independently, two sessions of one story counting that story once, deleted-story rows
  excluded from `m`, and `No sessions` plus the explanatory paragraph when the list is empty.

### Implementation for User Story 1

- [X] **T006** [US1] Add `src/components/Admin/AdminSessions.css` — page-scoped structure only
  (D8): fixed shell with the content area as the sole scroll container, full-width container
  with a 16px gutter and **no `max-width` wrapper**, kicker, the `ALL SESSIONS` label,
  monospace wrapping id cell, right-aligned `tabular-nums` numeric column, the italic
  deleted-story label, the 1%-width nowrap action column, and the caption. Follow
  `AdminAccounts.css` for anything the two screens share (contracts/ui.md §1).
- [X] **T007** [US1] Add `src/components/Admin/SessionsTable.jsx` — the `.table` with
  `<th scope="col">` headers in the design's order, the per-row cells, and a `sessions` prop.
  Render the actions column but leave the action slot to US2.
- [X] **T008** [US1] Rewrite `src/pages/AdminSessionsPage.jsx` onto the design's shell: import
  `AdminSessions.css`, render the `SESSIONS` kicker and the computed heading, the `ALL
  SESSIONS` label, `SessionsTable`, and the caption; render the empty state in place of the
  table when there are no sessions; keep the existing loading and error states. Derive both
  counts from the rows (data-model.md → *Client projection*), excluding the
  `(deleted story)` sentinel from the story count.

**Checkpoint**: the screen matches the design as a read-only surface. US2 and US3 are still
absent; the page is shippable and correct without them.

---

## Phase 4: User Story 2 — Delete a session, deliberately (P1)

**Goal**: An administrator can delete any listed session, always behind a confirmation.

**Independent Test**: Delete a row (player and test-play), cancel a delete, and force a failure
and a 404; the table always agrees with the server afterwards.

### Backend tests

- [X] **T009** [P] [US2] Extend `src/backend/tests/unit/test_play_session_service.py`:
  `delete_session_as_administrator` deletes a session owned by someone else and deletes
  regardless of `status` (`active`, `inactive`, `concluded`); raises `SessionNotFoundError` for
  an unknown id and for one that vanishes mid-delete; and — the guard that matters —
  `delete_player_session`'s ownership check is unchanged.
- [X] **T010** [P] [US2] Extend `src/backend/tests/unit/test_test_play_session_service.py`: the
  same for the test-play service, plus `Story.lastTestPlayedAt` untouched (so a story stays
  publishable after its test session is deleted) and `Story.totalTokens` not decremented.
- [X] **T011** [P] [US2] Extend `src/backend/tests/unit/test_session_overview_service.py`:
  `delete_session` finds a player session, finds a test-play session, and raises
  `SessionNotFoundError` when neither container holds the id — asserting it never reaches the
  second container once the first has deleted.
- [X] **T012** [US2] Extend `src/backend/tests/integration/test_admin_sessions_endpoint.py` for
  `DELETE /api/manage/sessions/{sessionId}`: 200 with the deleted body, 404 for an unknown id,
  403 for a signed-in non-administrator, 401 unauthenticated (contracts/api.md).

### Backend implementation

- [X] **T013** [P] [US2] Add `delete_session_as_administrator(session_id)` to
  `src/backend/services/play_session_service.py` — no owner check, `SessionNotFoundError` when
  absent, tolerant of a concurrent delete (D4).
- [X] **T014** [P] [US2] Add `delete_session_as_administrator(session_id)` to
  `src/backend/services/test_play_session_service.py`, same contract, never touching the
  `Story` (D4).
- [X] **T015** [US2] Add `delete_session(session_id)` to
  `src/backend/services/session_overview_service.py` — try the player service, fall back to the
  test-play service on `SessionNotFoundError`, re-raise if neither holds it (D3). Depends on
  T013, T014.
- [X] **T016** [US2] Add the `delete_session` handler to `src/backend/api/admin/sessions.py`
  behind `authorize_admin`, returning the shapes in contracts/api.md, and register
  `DELETE manage/sessions/{sessionId}` in `src/backend/function_app.py`.

### Frontend tests

- [X] **T017** [P] [US2] Add `tests/integration/admin_sessions_delete.test.jsx`: the row's
  Delete opens the dialog and deletes nothing; the dialog body names the id's first 8
  characters and the account; "Keep it", the backdrop and Escape each cancel leaving no pending
  state; confirming removes the row and recomputes the heading; a failed delete keeps the row
  and shows an `role="alert"` notice; a 404 removes the row and says it was already removed.
  Use synthetic addresses only (D10).

### Frontend implementation

- [X] **T018** [P] [US2] Add `deleteSession(token, sessionId)` to `src/services/sessionService.js`
  (contracts/api.md → *Frontend service surface*).
- [X] **T019** [US2] Add `src/components/Admin/SessionDeleteAction.jsx` — the ghost Delete
  button with the Lucide `trash-2` icon and a row-distinguishing accessible name, owning the
  dialog state and rendering `Common/ConfirmDeleteDialog` with the copy in contracts/ui.md §5
  (D8). **Not** to be confused with the existing `components/Home/SessionDeleteAction.jsx`
  (plan.md → *Naming collision*).
- [X] **T020** [US2] Wire it in: `SessionsTable` renders the action per row;
  `AdminSessionsPage` removes the row and recomputes the heading only on a confirmed server
  response, and renders the failure and already-removed notices (FR-014, FR-015 — never
  optimistic, research.md Decision 9).

**Checkpoint**: deletion works end to end from the admin's side. The player side is still
wrong — a player acting on a deleted session is told their *story* was deleted. US3 fixes that.

---

## Phase 5: User Story 3 — A player whose session is deleted lands somewhere sensible (P1)

**Goal**: `session_removed` exists, is distinct from `story_deleted`, and bumps the player to
Home with a dismissible message.

**Independent Test**: Delete a player's session as an admin, then act as that player from each
of the four entry points and land on Home with the dialog; separately, delete a *story* and
confirm the story-deleted outcome is unchanged.

### Backend tests

- [X] **T021** [P] [US3] Extend `src/backend/tests/integration/test_game_sessions_endpoint.py`:
  for each of `POST …/interactions`, `POST …/resume`, `GET …/{id}` and `POST …/checkpoints`, a
  missing session returns `404 session_removed` with the D6 message.
- [X] **T022** [P] [US3] In the same file, the paired regression: for each handler that has
  one, a **deleted story** still returns `404 story_deleted` and an **unpublished story** still
  returns `409 story_unpublished`, unchanged. These two outcomes shared a code path before this
  feature; this task is what proves they were separated rather than swapped.
- [X] **T023** [P] [US3] Assert `DELETE /api/game/sessions/{sessionId}` still returns
  `404 not_found`, deliberately unchanged (contracts/api.md → *Explicitly not changed*).

### Backend implementation

- [X] **T024** [US3] In `src/backend/api/game/sessions.py`, split the
  `except (SessionNotFoundError, AdventureNotFoundError)` handlers in `submit_interaction`,
  `resume_session` and `get_session` so `SessionNotFoundError` returns a new
  `_session_removed_response()` and `AdventureNotFoundError` keeps `_story_deleted_response()`;
  change `create_checkpoint`'s `SessionNotFoundError` branch from `404 not_found` to the same
  response (D5). Add the helper alongside the existing two.

### Frontend tests

- [X] **T025** [P] [US3] Extend `tests/Play/PlayPage.test.jsx`: on `session_removed` from a
  submit, a checkpoint save, and a refresh, the page raises `onSessionRemoved` and does **not**
  render an in-place notice or a "Return to your story list" button; `story_deleted` still
  renders its existing in-place notice unchanged.
- [X] **T026** [P] [US3] Add `tests/integration/home_session_removed.test.jsx`: a
  `session_removed` on the play surface lands on Home with the dialog; dismissing leaves a
  working Home with the session absent from In progress; a reload does not refire the dialog;
  and a Resume from a stale list raises the same outcome.

### Frontend implementation

- [X] **T027** [P] [US3] Add `src/components/Home/SessionRemovedDialog.jsx` — the design
  system's `.dialog`/`.dialog-backdrop` with `role="dialog"`, `aria-modal`, the D6 copy, and a
  single acknowledging action.
- [X] **T028** [US3] In `src/pages/PlayPage.jsx`, add an `onSessionRemoved` prop and branch to
  it on `err.response.data.error === "session_removed"` in `handleSubmit`, `handleRefresh`,
  `handleSaveCheckpoint` and `handleResume` — leaving, not noticing in place (D7).
- [X] **T029** [US3] In `src/pages/GamePage.jsx`, pass `onSessionRemoved` through to
  `navigate("/menu", { state: { sessionRemoved: true }, replace: true })`, and handle the same
  error on its own resume path so a stale Resume lands identically.
- [X] **T030** [US3] In `src/pages/HomePage.jsx`, read the one-shot route state, render
  `SessionRemovedDialog`, and clear the state on mount so a reload does not refire it
  (data-model.md → *Client state*).

**Checkpoint**: the loop closes — an admin deletes, the player is told the truth about what
happened and lands somewhere they can act.

---

## Phase 6: User Story 4 — Bring a stale Sessions list back in sync (P3)

**Goal**: The header's refresh control re-reads the list in place.

**Independent Test**: Trigger refresh; the table and heading redraw without leaving the screen,
and a failed refresh keeps the old table behind a notice.

- [X] **T031** [P] [US4] Add `tests/integration/admin_sessions_refresh.test.jsx`: refresh
  re-reads the list and recomputes the heading; a failed refresh keeps the previously loaded
  table visible behind an `role="alert"` notice and never blanks it (FR-016).
- [X] **T032** [US4] Wire `AdminSessionsPage` to `usePublishRefresh`/`useRefreshable` the way
  `AdminAccountsPage` and `HomePage` already do, replacing the page's hand-rolled `refresh`
  callback (D8) — and keep the existing table rendered on a refresh failure.

**Checkpoint**: all four stories are independently functional.

---

## Phase 7: Polish & cross-cutting

- [X] **T033** [P] Run `npm --prefix src/frontend run lint` and fix anything it reports in the
  files this feature touched.
- [X] **T034** [P] Confirm no token, colour, spacing or font literal was introduced outside
  `designTokens.css`, and that no button's interaction states are re-declared in
  `AdminSessions.css` (Principle VIII, D8).
- [X] **T035** Verify the accessibility bar on the new surfaces: the table is a real
  `<table>` with `<th scope="col">`; each row's Delete has an accessible name that
  distinguishes it from the other rows; both dialogs are keyboard-operable, dismissible with
  Escape, and return focus sensibly on close; `(deleted story)` carries its meaning as text,
  not colour.
- [X] **T036** Run the full gate: `pytest src/backend/tests` and
  `npm --prefix src/frontend run test`, in the devcontainer if one is running for this
  checkout. Record what actually ran and what it returned, for the PR description.
- [ ] **T037** Walk `quickstart.md`'s manual steps, including step 17 (deleting a *story* still
  yields the story-deleted message). Check the screen element by element against
  `08-admin-sessions-spec.md` (SC-003); D9 permits exactly two deviations — anything else found
  is a finding to fix, not to document.
- [ ] **T038** Open the PR per CLAUDE.md's *PR description* and *PR title format*. Title:
  `feat(frontend): …` is wrong here — the change spans backend, frontend and governance;
  pick the scope from `scripts/pr-title-config.js` that matches the primary surface and say so.
  **Recommended review tier: `ultra`** — `.specify/memory/constitution.md` is in CLAUDE.md's
  blast-radius list, which is always `ultra` whatever the diff size, and the change also adds a
  destructive endpoint. Ask the user to run it; Claude must not launch it.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: done.
- **Phase 2 (Foundational)**: T002 gates *shipping* every later phase, not building it — it can
  be written first or last, but the PR is not valid without it. T003 is independent of T002.
- **Phase 3 (US1)**: depends on nothing but T001. This is the MVP.
- **Phase 4 (US2)**: depends on US1 for the table it hangs the action on.
- **Phase 5 (US3)**: depends on US2 only for end-to-end demonstration; the `session_removed`
  split (T021–T024) is independently testable and is worth landing even alone, since it
  corrects existing behaviour.
- **Phase 6 (US4)**: depends on US1.
- **Phase 7**: depends on everything.

### Within each story

Tests first and failing; services before endpoints; endpoints before the frontend that calls
them; components before the page that composes them.

### Parallel opportunities

- T009, T010, T011 (three separate backend unit-test files).
- T013, T014 (two separate services) — then T015 joins them.
- T021, T022, T023 (same file — write together, but they are one edit, so treat as sequential
  if working in one branch).
- T025, T026, T027 (three separate frontend files).
- T033, T034 (independent checks).

---

## Implementation Strategy

### MVP

Phase 1 + Phase 3 (US1) alone is a complete, shippable improvement: the Sessions screen matches
the canonical design, read-only. It carries no governance amendment requirement of its own only
if T002 is also landed — the prototype reference is part of the contract either way.

### Incremental

1. US1 → the screen looks right.
2. US2 → deletion works from the admin's side. **Do not ship US2 without US3**: between the two,
   a player whose session is deleted is told their story was deleted, which is false.
3. US3 → the player side is honest.
4. US4 → refresh.

### The one ordering constraint that is not negotiable

US2 and US3 ship together. US3 may ship alone (it corrects existing behaviour); US2 may not.
</content>
