---
description: "Task list for People (admin) screen design-spec conformance (#333)"
---

# Tasks: People (Admin) Screen Design-Spec Conformance

**Input**: `/specs/030-people-admin-design-spec/` — spec.md, plan.md, research.md,
data-model.md, contracts/ui.md, quickstart.md.

**Canonical UI**: `specs/designs/05-admin-users-spec.md` (written spec) and
`specs/designs/05-admin-users.html` (mockup), vendored by T001, plus the updated
`specs/designs/styles.css` T001 also vendors. Together they are the acceptance reference for
the People screen and — for the button-language block — every screen.

## Binding decisions

Referenced by number below rather than restated in each task.

- **D1 — Canonical reference.** T001 vendors it; nothing else here can be checked against the
  design until it lands.
- **D2 — No Name column.** The Microsoft account email is the sole identity column; no name is
  added anywhere (spec.md *Scope note*; research.md Decision 1).
- **D3 — Two Status states only.** "Has signed in" (bound) and "Never signed in" (not bound). The
  design's third state ("Signed out · {relative time}") is never rendered (spec.md *Scope
  note*; research.md Decision 2).
- **D4 — Styling.** Page-scoped classes (`AdminAccounts.css`) are additive layout-only
  modifiers; every control keeps its design-system class (`btn btn-primary`, `btn
  btn-secondary`, `btn btn-ghost`, `table`, `tag tag-accent`, `tag tag-outline`,
  `dialog-backdrop`, `dialog`, `input`, `field`). Interaction-state styling for buttons lives
  only in `designTokens.css`'s new shared block, never re-declared per page (research.md
  Decision 4).
- **D5 — Button-language block is app-wide.** T0xx vendoring it into `designTokens.css`
  affects every screen using `.btn-*`/`.nav a`, not just People — this is intentional per the
  issue's own text (research.md Decision 4).
- **D6 — One backend field.** The only backend change is serializing `dateAdded` in
  `_account_summary()` (FR-008). No new endpoint, no schema change.
- **D7 — SC-003 allows exactly two exceptions.** The Name column (D2) and the third Status
  state (D3). Any third gap found in T020 is a finding, not an exception.

## Conventions

- IDs run in execution order. `[P]` marks a task that may run alongside other `[P]` tasks in
  the same phase; different files, no dependency on an incomplete task.
- `[US1]`/`[US2]`/`[US3]` map a task to its spec.md user story.
- Tests precede the implementation they cover and MUST fail first (constitution Principle I).
- Paths are relative to the repo root; `src/`/`tests/` under `src/frontend/` unless prefixed
  `src/backend/`.
- Commit at each checkpoint.

---

## Phase 1: Setup — canonical design reference

- [X] **T001** Vendor issue #333's attachments into `specs/designs/`: replace
  `05-admin-users.html` and `styles.css` with the attached versions, and add
  `05-admin-users-spec.md`. Update `specs/designs/README.md`'s People (05) note to record that
  `030-people-admin-design-spec` supersedes the old markup, name the button-language block now
  in `styles.css` as app-wide, and record D2/D3 as deliberate non-implementations (already
  drafted in this session — verify it matches the final vendored files).

**Checkpoint**: the canonical reference is in the repo and the README agrees with it.

---

## Phase 2: Foundational — shared button language (blocks every story's visual verification)

**Purpose**: The design's button treatment (2px visible border at rest, animated hover/press,
nav underline) must exist in the app's token layer before any story's UI can be checked
against the canonical mockup.

- [X] **T002** Append the canonical `styles.css`'s shared button-interaction block (`.btn`
  transition; `.btn-secondary`/`.btn-primary`/`.btn-ghost` border/hover/press rules; `.nav a`
  bottom-border states) to `src/frontend/src/styles/designTokens.css`, in the same relative
  position (after the existing button rules), matching D5. Do not remove or rewrite the
  existing rules — this is additive only.
- [X] **T003** [P] Manually verify (per quickstart.md step 10) that an unrelated screen already
  using `.btn-primary`/`.btn-secondary` (e.g. Home's primary action, or the admin Stories list)
  picks up the new border/hover/press treatment with no code change on that screen.

**Checkpoint**: every `.btn-*`/`.nav a` control app-wide shows the new interaction language.
User story work can now begin.

---

## Phase 3: User Story 1 - See every account and who can sign in, at a glance (Priority: P1) 🎯 MVP

**Goal**: The People screen's shell, heading, two-column grid, and accounts table match the
canonical design, with an honest two-state Status column and an Added column.

**Independent Test**: Load `/admin/accounts` with several accounts in different
bound/never-bound and single/dual-role states; confirm the table and layout match
`05-admin-users-spec.md` §2–§6 (minus D2/D3's two named exceptions).

### Tests for User Story 1

> Write these first; confirm they fail before implementing.

- [X] **T004** [P] [US1] In `src/backend/tests/integration/test_admin_accounts_endpoint.py`,
  update `test_list_accounts_returns_every_entry_with_email_and_roles` and
  `test_add_account_*`'s exact-shape assertions (the `body["account"] ==` / `body["accounts"]
  ==` checks) to include `"dateAdded"`, and add a new test asserting `dateAdded` is `None` for
  an entry created with no `dateAdded` set and the ISO string for one that has it.
- [X] **T005** [P] [US1] In `src/frontend/tests/components/AccountList.test.jsx`, add
  assertions: a bound account's row shows "Has signed in" text and a `.status-on` dot; a
  never-bound account's row shows "Never signed in" and a `.status-off` dot; the design's
  third-state text ("Signed out") never appears anywhere; a `Player`-only account renders a
  `tag-outline` tag and an `Administrator`-holding account renders a `tag-accent` tag; a row
  with a `dateAdded` value renders a short formatted date, and a row with none renders no
  placeholder text.
- [X] **T006** [P] [US1] In `src/frontend/tests/integration/admin_accounts.test.jsx`, add an
  assertion that the page heading reads `{n} accounts in LLM Dungeon` where `n` matches the
  loaded account count, and that the accounts table and add-account panel both render within
  the page (grid presence, not exact pixel layout).

### Implementation for User Story 1

- [X] **T007 [US1]** In `src/backend/api/admin/accounts.py`, add `"dateAdded": entry.dateAdded`
  to `_account_summary()`'s returned dict (D6, FR-008). Run T004 to confirm it now passes.
- [X] **T008 [P] [US1]** Create `src/frontend/src/components/Admin/AdminAccounts.css`
  (page-scoped, mirrors `Home.css`/`Play.css`): the `PEOPLE` kicker treatment, the `.hr`
  spacing, the `.people-grid` two-column layout (`repeat(auto-fit, minmax(min(100%, 420px),
  1fr)); gap: 40px; align-items: start`), and the Status classes
  (`.status`/`.status .dot`/`.status-on .dot`/`.status-off .dot`/`.status-off`) exactly as
  `05-admin-users-spec.md` §6.1 specifies (square dot, no border-radius).
- [X] **T009 [US1]** Rewrite `src/frontend/src/pages/AdminAccountsPage.jsx`: drop the
  `max-width` wrapper, add the `PEOPLE` kicker + `<h2>{accounts.length} accounts in LLM
  Dungeon</h2>` heading, wrap `AccountList`/`AccountForm` in `.people-grid`, add the muted
  caption below the table ("Removing an account revokes access at the next sign-in. Stories
  the player has finished stay in the class record."), and import `AdminAccounts.css`.
- [X] **T010 [US1]** In `src/frontend/src/components/Admin/AccountList.jsx`: reorder/update
  table columns to Microsoft account / Role / Status / Added / *(actions)*; change
  `ROLE_TAG_CLASS` so `Player → "tag tag-outline"` (Administrator stays `"tag tag-accent"`,
  research.md Decision 5); replace the current Status cell text (`"Signed in"`/`"Pending first
  sign-in"`) with the `.status`/`.status-on`/`.status-off` dot-plus-label markup per D3; add an
  Added cell rendering a short-formatted `account.dateAdded` (small local formatter, mirroring
  `AdminPage.jsx`'s `formatLastPublished`, rendering nothing when absent); keep the Remove
  button's existing eligibility logic, restyled to `padding: 6px 10px; font-size: 12px` per
  design spec §6; add `overflow-wrap: anywhere` to the Microsoft-account cell (FR-006).
- [X] **T011 [US1]** Run T004–T006 and confirm they pass; run the full existing
  `test_admin_accounts_endpoint.py`, `AccountList.test.jsx`, and `admin_accounts.test.jsx`
  suites and confirm nothing else regresses.

**Checkpoint**: User Story 1 fully functional and testable independently — the table and shell
match the canonical design (minus D2/D3).

---

## Phase 4: User Story 2 - Add and remove accounts without losing existing safeguards (Priority: P1)

**Goal**: The add-account panel and remove-confirmation flow match the canonical design's
"Add someone" panel, with every existing safeguard (role-required, confirmation, self/seed
protection) unchanged.

**Independent Test**: Add an account through the restyled panel and confirm it appears in the
table; remove a non-self, non-seed-admin account and confirm the confirmation dialog still
gates it.

### Tests for User Story 2

- [X] **T012** [P] [US2] In `src/frontend/tests/components/AccountForm.test.jsx`, add
  assertions: the panel renders the `.ovnum` "+", the "Add someone" heading, the muted
  Microsoft-account-sign-in line, both role checkboxes' descriptive text ("Sees only the
  stories assigned to their class." / "Creates and edits stories, adds and removes
  accounts."), and the submit button as `.btn.btn-primary.btn-block`; existing
  submit/validation-error behavior assertions are unchanged.
- [X] **T013** [P] [US2] In `src/frontend/tests/components/AccountList.test.jsx` (or a
  dedicated removal test if one already exists — check first), confirm the confirmation
  dialog's markup/copy is unchanged and that self/seed-admin rows still render no Remove
  action — regression coverage only, no new behavior.

### Implementation for User Story 2

- [X] **T014 [US2]** Restyle `src/frontend/src/components/Admin/AccountForm.jsx` into the
  "Add someone" panel per `05-admin-users-spec.md` §7: `.ovnum` `+`, `<h3>`, muted intro line,
  labelled Microsoft-account field (placeholder `ada.bell@school.internal`), a "Roles — choose
  one or both" field with the two checkbox rows and their descriptions, the muted note below
  them, `.hr`, and `.btn.btn-primary.btn-block` "Add account" with the label flush left. Keep
  existing state/validation/submit logic (`hasPlayer`/`hasAdministrator`/`MESSAGES`) unchanged.
  Panel container styling (border/background/padding) added to `AdminAccounts.css` (T008) or
  inline token-based styles, per D4.
- [X] **T015 [US2]** Run T012–T013 and confirm they pass; run the existing
  `AccountForm.test.jsx` and any removal-flow tests in full and confirm no regression.

**Checkpoint**: User Stories 1 and 2 both work independently — the full People screen matches
the canonical design end-to-end (minus D2/D3), and every add/remove safeguard is unchanged.

---

## Phase 5: User Story 3 - Recover a stale People screen without losing in-progress input (Priority: P3)

**Goal**: Confirm the header Refresh control (already wired via `019-spa-refresh-button`'s
`RefreshContext`/`usePublishRefresh` — `AdminAccountsPage.jsx` already calls it) continues to
work against the restyled screen, and add regression coverage if none exists.

**Independent Test**: Trigger the header's Refresh control on the restyled People screen and
confirm the table re-reads from the server without navigating away.

### Tests for User Story 3

- [X] **T016** [P] [US3] Check `src/frontend/tests/integration/admin_accounts_refresh.test.jsx`
  for existing coverage of a successful refresh and a failed refresh (notice shown, table
  retained). If either is missing, add it; otherwise confirm both already pass unchanged
  against the restyled page (no new assertions needed — this story requires no new code).

### Implementation for User Story 3

- [X] **T017 [US3]** No production code change expected (Refresh is already wired). If T016
  surfaces a gap caused by the restyle (e.g. a selector the test relies on moved), fix the
  minimal selector/markup issue in `AdminAccountsPage.jsx`/`AccountList.jsx` only.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] **T018** [P] Remove now-dead inline styles left over from the pre-restyle
  `AdminAccountsPage.jsx`/`AccountList.jsx`/`AccountForm.jsx` (e.g. any leftover `style={{...}}`
  the design-system classes now replace).
- [X] **T019** Run the full frontend suite (`npx vitest run`) and full backend suite (`pytest`)
  and confirm no unrelated regression.
- [X] **T020** Walk `05-admin-users-spec.md` section by section against the implemented screen
  (SC-003) and confirm every element is present in the position the design gives it, with
  exactly the two documented exceptions (D2, D7). Record the walkthrough result in the PR
  description. Result: conformant, with the two documented exceptions (no Name column/field;
  two-state Status). This walkthrough also caught and fixed two fidelity gaps: the hr's
  `20px 0 32px` spacing had drifted, and the design's own wrapping div around the two role
  checkboxes turned out to be load-bearing — without it, `designTokens.css`'s
  `.field > label { display: block }` rule outranks `.people-role-option`'s `display: flex` on
  specificity, silently breaking the checkbox-row layout.
- [ ] **T021** Run `quickstart.md` end-to-end (all 10 steps) against a local dev environment.
  Not run this session — no local Cosmos DB emulator / Azure Functions host was started, so
  this needs a manual pass (or CI) before merge; steps 1-9 are covered by the automated
  integration tests above, but a real-browser check (step 10 especially) has not happened.
- [X] **T022** `/code-review high` pass and fixes. Findings and outcomes:
  - **HIGH, fixed** — `AccountList` returned a fragment with 3 always-rendered top-level
    siblings; combined with `AccountForm`'s panel that made `.people-grid` lay out 4 items
    instead of 2, misplacing the table and panel at common viewport widths. Fixed by
    wrapping the label/table/caption in one `min-width: 0` div (matches the canonical
    mockup's own wrapping div). Regression test added
    (`admin_accounts.test.jsx`: "wraps the accounts table and the add-account panel as
    exactly two grid items").
  - **MEDIUM, fixed** — `.people-shell { height: 100vh }` inside `AuthenticatedLayout`'s
    nav-plus-flex:1 shell produced a page-level scroll that carried the nav off-screen.
    Changed to `height: 100%`, matching `Play.css`'s `.play-shell` (the newer, correct
    precedent) rather than `Home.css`'s `.home-shell` (the older, buggy one this was
    copied from).
  - **MEDIUM, fixed** — no mobile breakpoint existed, so the fixed-viewport shell stayed
    on at phone widths, risking clipped content under a mobile URL bar. Added the same
    `@media (max-width: 760px)` relaxation `Home.css` uses.
  - **MEDIUM, fixed** — the heading read "0 accounts in LLM Dungeon" during the initial
    load (and after a failed first load), asserting a count before any data arrived.
    Now renders a plain "People" heading until `accounts` is non-null. Regression test
    added ("never states a count before the first load resolves").
  - **MEDIUM, fixed** — the new global `.btn-secondary`/`.btn-primary`/`.btn-ghost` hover
    rules had higher specificity than the existing disabled-state rule's intent, so an
    `aria-disabled` control (e.g. `StatusPanel`'s hint button) lit up with a full-accent
    hover fill on mouseover, reading as live. Scoped every new hover/active selector with
    `:not(:disabled):not([aria-disabled="true"])`. Not covered by an automated test —
    jsdom doesn't exercise `:hover` — verified by reading the resulting cascade;
    recorded as a manual-verification item.
  - **LOW/MEDIUM, addressed as documentation** — the button-language block's comment
    called itself "additive," which undersold that it also changes several controls'
    *resting* colors app-wide (`.btn-ghost` ink, `.btn-secondary` background), and no
    non-People screen was manually checked. Corrected the framing in code comments and
    research.md Decision 4, and named the unchecked screens as a known limitation.
  - **LOW, fixed** — the bound Status label "Signed in" paired with the accent dot read
    as live presence, which `bound` doesn't mean (only "signed in at least once, ever").
    Changed the label to "Has signed in" across code, tests, and every spec doc.
  - **LOW, fixed** — the "Roles — choose one or both" `<label>` wrapped no control and had
    no `htmlFor` (an orphan label). Changed to a `<span>` with `role="group"`/
    `aria-labelledby` on the checkbox group's container div.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 (needs the vendored canonical `styles.css` to
  copy from) — BLOCKS all user stories' visual verification (not their non-visual test
  assertions, which may be written earlier).
- **User Stories (Phase 3+)**: Depend on Foundational. US1 and US2 touch overlapping files
  (`AdminAccountsPage.jsx`, `AdminAccounts.css`) and should be done in order (US1 then US2) to
  avoid merge friction, though US2's own logic doesn't depend on US1's completion. US3 requires
  no new code and can be verified any time after US1.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Parallel Opportunities

- T003 alongside T002 is not truly parallel (T003 verifies T002's output) — listed [P] only in
  the sense it touches no file T002 owns.
- T004, T005, T006 (different files) run in parallel.
- T012, T013 (different files) run in parallel.
- T016 has no file conflict with Phase 3/4 tasks and may be drafted early, though it's only
  meaningfully verifiable once Phase 3/4 land.

---

## File ownership (avoid same-file conflicts)

| File | Tasks |
| --- | --- |
| `specs/designs/05-admin-users.html`, `05-admin-users-spec.md`, `styles.css`, `README.md` | T001 |
| `src/frontend/src/styles/designTokens.css` | T002 |
| `src/backend/api/admin/accounts.py` | T007 |
| `src/backend/tests/integration/test_admin_accounts_endpoint.py` | T004 |
| `src/frontend/src/components/Admin/AdminAccounts.css` | T008, T014 |
| `src/frontend/src/pages/AdminAccountsPage.jsx` | T009, T018 (dead-style cleanup only) |
| `src/frontend/src/components/Admin/AccountList.jsx` | T010, T018 |
| `src/frontend/src/components/Admin/AccountForm.jsx` | T014, T018 |
| `src/frontend/tests/components/AccountList.test.jsx` | T005, T013 |
| `src/frontend/tests/components/AccountForm.test.jsx` | T012 |
| `src/frontend/tests/integration/admin_accounts.test.jsx` | T006 |
| `src/frontend/tests/integration/admin_accounts_refresh.test.jsx` | T016 |

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (T001) → Phase 2 (T002–T003) → Phase 3 (T004–T011).
2. **STOP and VALIDATE**: the accounts table and shell already match the canonical design.

### Incremental Delivery

1. Setup + Foundational → button language and canonical reference in place.
2. US1 → table/shell conformance → independently testable.
3. US2 → add/remove panel conformance → independently testable.
4. US3 → confirm Refresh still works → independently testable (near-zero new code).
5. Polish → full-suite regression pass + SC-003 walkthrough + quickstart run.
