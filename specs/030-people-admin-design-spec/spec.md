# Feature Specification: People (Admin) Screen Design-Spec Conformance

**Feature Branch**: `030-people-admin-design-spec`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "Implement the People (admin) screen UI per GitHub issue #333
(https://github.com/RezaMahmood/llm-dungeon/issues/333). The issue says: 'The people admin
screen should be styled as follows. This is the canonical design for this page. Note the
updated styles.css which now encapsulates design language for all buttons across the app'
and attaches specs/designs/05-admin-users.html, specs/designs/05-admin-users-spec.md, and an
updated specs/designs/styles.css as the canonical reference — a full-viewport, no-page-scroll
admin screen with a fixed nav, a page heading stating the account count, a two-column body (an
accounts table on the left, an add-account panel on the right), a Status column showing
sign-in state per account, and a remove-confirmation dialog. The existing
AdminAccountsPage/AccountList/AccountForm components (014-account-listing) already implement
much of this with ad hoc styling and a two-state status ('Signed in'/'Pending first
sign-in'); this feature should bring them into conformance with the canonical
05-admin-users-spec.md/05-admin-users.html, using shared CSS classes instead of ad hoc inline
styles where the design system calls for page-scoped structural rules, without breaking any
existing account-add/account-remove/role-management behavior (014-account-listing)."

## Scope note: honest data, not the design's literal fields

This is a design-conformance feature. Where the canonical design shows a data field or a
state the application cannot honestly produce today, **this feature builds the closest
honest rendering of that part of the screen using data the backend already has, and states
the gap as an Assumption — it does not invent a name or a live-presence signal that does not
exist.** No stand-in or fabricated data is used to make a column appear to match the mockup
literally.

This applies to two parts of the design:

1. **The "Name" column.** `ProvisionedAccountEntry` (014-account-listing) has no display-name
   field — only `email`. This feature does not add name collection (out of scope; a separate
   feature would need to specify where a name comes from — self-reported at first sign-in,
   an admin-entered field, or read from the directory). The table keeps a single identity
   column showing the Microsoft account email, matching what `04-admin-wizard`-adjacent
   screens already do elsewhere, rather than showing a fabricated or duplicated name.
2. **The three-state Status column.** The backend can tell "never signed in" (no bound
   `objectId`) apart from "has signed in" (bound), and it stores a one-time `dateBound` (the
   *first* sign-in), but it has no live session/presence tracking, so it cannot tell a
   currently-active session apart from one that signed in once, long ago. This feature
   renders two honest states — **"Signed in"** (bound) and **"Never signed in"** (not
   bound) — using the dot-plus-label treatment the design specifies, and does not render the
   design's third state ("Signed out · {relative time}"), which would require inventing a
   presence signal the backend cannot support. Live presence/last-seen tracking is specified
   separately.

Every other affordance here reuses data the application already produces (`roles`,
`isSeedAdmin`) or an implementation pattern the application already has (the header's Refresh
control, `019-spa-refresh-button`), or exposes a field the backend already stores but does not
yet serialize (`dateAdded`, per FR-008).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See every account and who can sign in, at a glance (Priority: P1)

An administrator managing the class roster wants to see, for every provisioned account, their
Microsoft account, their role(s), whether they have ever signed in, and when they were added —
laid out the way the canonical design shows it, without a page scrollbar hiding rows below the
fold.

**Why this priority**: This is the core purpose of the screen (issue #333): a single glance at
the table tells the administrator the state of every account. Without correct layout and an
honest status column, the screen still lists accounts but does not deliver the at-a-glance
review the design calls for.

**Independent Test**: Load the People screen with several provisioned accounts in different
states (bound/never-bound, single-role/dual-role) and confirm the table shows the Microsoft
account, a role tag group, an honest sign-in status, and an added date for each row, laid out
in the design's two-column grid with no page-level scrollbar.

**Acceptance Scenarios**:

1. **Given** an account that has completed sign-in at least once, **When** the table renders
   its row, **Then** the Status cell shows the accent dot and the label "Signed in".
2. **Given** an account that was added but has never completed sign-in, **When** the table
   renders its row, **Then** the Status cell shows the neutral dot and the label "Never signed
   in".
3. **Given** an account holding both the Player and Administrator roles, **When** the table
   renders its row, **Then** both role tags appear in the Role cell, each in the design's
   distinct tag style.
4. **Given** the People screen is loaded on a desktop-width viewport, **When** the page
   renders, **Then** the outer page does not scroll — only content within the shell scrolls if
   it overflows — and the accounts table and add-account panel sit in the design's two-column
   grid, with the panel dropping below the table on narrow viewports.

---

### User Story 2 - Add and remove accounts without losing existing safeguards (Priority: P1)

An administrator adds a new person's Microsoft account with one or both roles, and later
removes an account that no longer needs access, using the styling and layout the canonical
design shows, while keeping every existing safeguard (role required, confirmation before
removal, self-removal and seed-administrator protection).

**Why this priority**: Ranked equal to User Story 1 because these are the screen's only two
state-changing actions; a visual restyle that broke either would make the redesign a
regression, not an improvement.

**Independent Test**: Add an account through the add-account panel and confirm it appears in
the table; then remove a non-self, non-seed-admin account through the row action and confirm
it requires the confirmation dialog before disappearing from the table.

**Acceptance Scenarios**:

1. **Given** the add-account panel, **When** the administrator submits a name-less Microsoft
   account and at least one role, **Then** the account is added and appears in the table
   without a page reload.
2. **Given** the add-account form, **When** the administrator attempts to submit with neither
   role checked, **Then** submission is blocked or rejected with the existing "select at least
   one role" message.
3. **Given** a removable account's row, **When** the administrator selects its Remove action,
   **Then** a confirmation dialog names the account and requires an explicit confirmation
   before the account is removed — selecting away or "Keep it" leaves the account untouched.
4. **Given** the currently signed-in administrator's own row, or the seed administrator's row,
   **When** the table renders, **Then** no Remove action is offered for that row, matching
   existing protections.

---

### User Story 3 - Recover a stale People screen without losing in-progress input (Priority: P3)

An administrator who suspects the account list is out of date (e.g. another administrator just
added someone) wants to bring it back in sync without leaving the screen or losing anything
they had already typed into the add-account form.

**Why this priority**: Extends the refresh capability already available elsewhere in the app
(019-spa-refresh-button) to this screen's header, for consistency; ranked last because it is a
recovery path, not the screen's primary purpose.

**Independent Test**: Trigger the header's refresh control on the People screen and confirm
the accounts table reloads from the server's current list while the screen stays put.

**Acceptance Scenarios**:

1. **Given** the administrator is on the People screen, **When** they select the header's
   refresh control, **Then** the accounts table is re-drawn from the server's currently stored
   list, and the administrator stays on the People screen throughout.
2. **Given** the refresh fails (e.g. a network problem), **When** the administrator retries or
   waits, **Then** the existing table remains visible and a clear notice explains the refresh
   did not succeed.

---

### Edge Cases

- What happens when there are zero provisioned accounts (should not occur in practice, since a
  seed administrator always exists, but the table must not break)? → The table renders its
  header row with an empty body rather than erroring.
- What happens when an account's Microsoft account address is very long? → It wraps rather
  than widening the table or pushing the row actions off-screen, per the design's
  `overflow-wrap: anywhere` rule.
- What happens if the account list can't be loaded at all (first load, not a refresh)? → A
  clear loading or error state is shown in place of the table; no stale or fabricated rows are
  shown.
- What happens on viewports narrower than the two-column breakpoint? → The add-account panel
  moves below the table; neither column is clipped or requires horizontal scrolling.
- What happens when an administrator tries to remove their own account or the seed
  administrator's account via a direct API call, bypassing the UI's hidden Remove action? →
  Unchanged: the server-side checks already enforced by 014-account-listing continue to reject
  it; this feature only touches presentation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The People screen MUST present a fixed, non-scrolling page shell in which the
  nav stays pinned and the page's own content does not introduce a page-level scrollbar under
  normal account-list lengths, per the canonical design's shell contract.
- **FR-002**: The page heading MUST state the number of provisioned accounts in a single
  sentence (e.g. "N accounts in LLM Dungeon"), updating whenever the list changes (add,
  remove, or refresh).
- **FR-003**: The body MUST lay out the accounts table and the add-account panel as a
  two-column grid on wide viewports, with the add-account panel moving below the table on
  narrow viewports, matching the canonical design's responsive behavior.
- **FR-004**: The accounts table MUST show, per account: the Microsoft account (email), one
  role tag per held role (Player and/or Administrator, visually distinguished from each
  other), a sign-in status, the date the account was added, and — where removal is permitted
  for that row — a Remove action.
- **FR-005**: The sign-in status (FR-004) MUST show exactly one of two honest states per the
  *Scope note*: "Signed in" (the account has completed at least one sign-in) or "Never signed
  in" (it has not), each with the design's dot-plus-label treatment and its own dot color.
  The design's third state ("Signed out · {relative time}") MUST NOT be implemented in this
  feature (see *Scope note*).
- **FR-006**: Long Microsoft account addresses MUST wrap within their table cell rather than
  widening the table or displacing the row's action control.
- **FR-007**: Removing an account MUST always require an explicit confirmation step naming the
  account before it is removed; there MUST be no way to remove an account directly from the
  table row without that confirmation.
- **FR-008**: The accounts list MUST expose each account's added date to the client (the
  backend already stores `dateAdded`; this feature serializes it on the list response) and the
  table MUST show it in a short, human-readable form.
- **FR-009**: The screen MUST continue to hide the Remove action for the signed-in
  administrator's own row and for the seed administrator's row, and MUST continue to require
  at least one role when adding an account — unchanged from existing behavior
  (014-account-listing).
- **FR-010**: The page's header MUST offer a refresh action — consistent with the refresh
  capability already available on other authenticated screens — that re-reads the accounts
  list from the server without requiring the administrator to leave the screen.
- **FR-011**: A failed refresh (FR-010) or a failed initial load MUST show a clear notice and
  MUST NOT silently replace the visible list with an empty or fabricated one.
- **FR-012**: The screen's visual presentation (spacing, color, type sizes, table styling, and
  button styling) MUST be built from the project's shared design system — including the
  centralized `.btn-primary`/`.btn-secondary`/`.btn-ghost` button treatments now defined once
  in `styles.css` — rather than page-specific ad hoc styles or inline style overrides for
  buttons.
- **FR-013**: None of the above MUST change or remove any existing account add, merge, remove,
  self-removal-prevention, or seed-administrator-protection behavior already delivered by
  014-account-listing.

### Key Entities

- **Provisioned Account**: A Microsoft account permitted to sign in — its email, the role(s)
  it holds (Player and/or Administrator, at least one), whether it has ever completed
  sign-in, the date it was added, and whether it is the protected seed administrator.
- **Sign-in Status**: One of two states this feature renders — "signed in" (has bound to a
  Microsoft identity at least once) or "never signed in" (added but not yet bound). A third,
  time-aware "signed out" state exists in the canonical design but is out of scope here (see
  *Scope note*).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator looking at the People screen can state, for any account, its
  Microsoft account, its role(s), and whether it has ever signed in, within a single glance —
  with no additional click, scroll, or navigation.
- **SC-002**: Across account lists of 0, 1, 6, and 20+ accounts, the nav and page heading
  occupy the same fixed position in all cases — only the table's own content grows.
- **SC-003**: Every element the canonical design places on the People screen is present, in
  the position the design gives it — verified element by element against
  `specs/designs/05-admin-users-spec.md` and `05-admin-users.html`. The two documented
  exceptions are the *Scope note*'s Name column and third Status state, both of which this
  spec deliberately renders differently for data-honesty reasons.
- **SC-004**: An administrator who believes the account list is out of date can bring it back
  in sync in a single action, without losing anything already typed into the add-account form.
- **SC-005**: Every automated regression test covering existing account add/merge/remove and
  role-requirement behavior (014-account-listing) continues to pass unchanged in what it
  verifies.

## Assumptions

- The "Name" column in the canonical design is not implemented (see *Scope note*): the
  backend has no display-name field, and inventing one (echoing the email's local part, for
  example) would misrepresent data the system does not actually have. A follow-up feature
  would need to decide where a name comes from before this column can be added honestly.
- The Status column renders two of the canonical design's three states (see *Scope note*):
  "Signed in" and "Never signed in". The third state, "Signed out · {relative time}", requires
  live session/presence tracking the backend does not have today (only a one-time first-bind
  timestamp) and is specified separately.
- "Refresh" (FR-010/FR-011) re-reads the same account list from the server, matching the
  meaning "refresh" already has on every other authenticated screen
  (019-spa-refresh-button) — it is not a new kind of sync.
- The centralized button language (FR-012) is additive to `styles.css`'s existing
  `.btn-primary`/`.btn-secondary`/`.btn-ghost` rules (per the canonical `styles.css`, which
  layers a shared interactive-button block after the existing declarations) rather than a
  breaking rename, so no other screen's markup needs to change for this feature to adopt it.
- Responsive behavior below the design's two-column breakpoint, and any bulk-action,
  class/group assignment, or audit-history affordances, remain out of scope, matching the
  canonical design spec's own stated exclusions (`05-admin-users-spec.md` §12).
