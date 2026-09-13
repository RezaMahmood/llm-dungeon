# Feature Specification: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Feature Branch**: `031-sessions-admin-design-spec`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "Implement the Sessions (admin) screen per GitHub issue #335
(https://github.com/RezaMahmood/llm-dungeon/issues/335). The issue says: 'The Sessions Admin
page should be styled as follows: [08-admin-sessions.html] [08-admin-sessions-spec.md]. As per
the design there should be a button that allows the deletion of a session. On deletion of the
session, if a player is in the middle of a session they are bumped back to the home page with
a pop up stating that their session has been removed. The session should simply be removed
from the player's game session list.' The canonical design references are
`specs/designs/08-admin-sessions.html` and `specs/designs/08-admin-sessions-spec.md`. This
replaces the existing read-only AdminSessionsPage (026-token-usage, FR-015/FR-016/FR-018) and
adds administrator session deletion end to end, including what a player sees when the session
they are playing is deleted underneath them."

## Scope note: this feature supersedes the read-only Sessions page

`026-token-usage` FR-016 states the Sessions page "MUST be read-only: it MUST NOT provide any
way to create, edit, or delete a session or its data", and the constitution's
**Administrator — sessions** screen contract describes a read-only list with no prototype
screen. Issue #335 reverses both deliberately: the page gains a per-row destructive action and
a canonical prototype. This feature therefore carries two governing-document changes as part of
its own scope:

1. **`026-token-usage` FR-016 is superseded** by FR-006 below. Every other requirement of
   026's Sessions page (FR-015, FR-017, FR-018 — what each row shows, the nav item, and the
   zero-token rendering) stays in force and is restated here where the design refines it.
2. **The constitution's Sessions screen contract is amended** to name
   `specs/designs/08-admin-sessions.html` and `08-admin-sessions-spec.md` as its acceptance
   reference and to permit the delete affordance. The screen may not ship ahead of that
   amendment (Governance: "No feature may ship a screen that is not traceable to a screen
   contract above or to a documented amendment extending one").

## Scope note: honest data, not the design's literal claims

Where the canonical design states something the application cannot honestly produce, this
feature builds the closest honest rendering and records the gap as an Assumption rather than
fabricating data. Two parts of the design are affected:

1. **The table caption's "Token totals stay in the usage record."** The application has no
   separate per-session usage ledger: a player session's `totalTokens` lives on the session
   document itself, so deleting the session does remove that number from the Sessions list.
   What survives is (a) the per-LLM-call telemetry in the observability sink, which
   Principle VI already requires and which this feature does not touch, and (b) a story's own
   cumulative `totalTokens`, into which admin test-play usage was already folded at the time
   it was spent and which this feature never decrements. The caption is rendered with wording
   that is true of those two records rather than implying a ledger that does not exist.
2. **The heading's story count.** The design counts distinct stories across the listed
   sessions, excluding deleted ones. The list already labels a session whose story is gone as
   `(deleted story)`, so the count is derived from the rows themselves — no separate story
   census is requested from the server.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review every session at a glance (Priority: P1)

An administrator doing housekeeping — or hunting for a session that has burned an unusual
number of tokens — opens Sessions and reads the whole instance's play activity off one table:
which story each session belongs to, its identifier, what it has cost in tokens, and whose
account owns it.

**Why this priority**: This is the screen's original purpose (026-token-usage FR-015) and the
precondition for every other action on it. Without a correct, legible table the delete action
has nothing trustworthy to act on.

**Independent Test**: Load Sessions with a mix of session kinds — player and admin test-play,
zero-token and high-token, live story and deleted story — and confirm each row shows its story
(or the deleted-story label), its full session identifier, a thousands-separated right-aligned
token total, and its account, under a heading stating the session and story counts.

**Acceptance Scenarios**:

1. **Given** sessions belonging to three distinct live stories, **When** the page renders,
   **Then** the heading reads "{n} sessions across 3 stories" with the correct session count.
2. **Given** exactly one session belonging to one story, **When** the page renders, **Then**
   the heading singularises to "1 session across 1 story".
3. **Given** a session whose story has since been deleted, **When** its row renders, **Then**
   the Story cell shows a visually distinct "(deleted story)" label rather than an empty cell,
   and that story is not counted in the heading's story total.
4. **Given** a session that has recorded no turns, **When** its row renders, **Then** the
   Total tokens cell shows `0`, not a dash or a blank.
5. **Given** a session with a token total in the thousands, **When** its row renders, **Then**
   the number is thousands-separated and right-aligned, and aligns digit-for-digit with the
   other rows' totals.
6. **Given** the Sessions screen on a desktop-width viewport, **When** the page renders,
   **Then** the outer page does not scroll — only the content area below the fixed nav scrolls
   — and the table never requires horizontal scrolling, long identifiers and account addresses
   wrapping within their cells instead.
7. **Given** no sessions exist at all, **When** the page renders, **Then** the heading reads
   "No sessions" and an explanatory sentence replaces the table.

---

### User Story 2 - Delete a session, deliberately (Priority: P1)

An administrator decides a session should go — an abandoned run, a test session that served
its purpose, a session that has run up an unreasonable token total. They remove it from the
row, confirming first against a dialog that names which session they are about to destroy.

**Why this priority**: This is the capability issue #335 adds, and the reason the screen is
being revisited at all. It is equal in priority to User Story 1 because the delete action is
unusable without the table that identifies its target.

**Independent Test**: Select a row's Delete action, confirm the dialog names that session and
its account before anything is destroyed, confirm the deletion, and verify the row disappears,
the heading recomputes, and the session is gone from the server's list on a fresh load.

**Acceptance Scenarios**:

1. **Given** any row in the table, **When** the administrator selects its Delete action,
   **Then** nothing is deleted yet and a confirmation dialog appears naming the session by a
   short prefix of its identifier and by its account.
2. **Given** the confirmation dialog is open, **When** the administrator chooses to keep the
   session (or otherwise dismisses the dialog), **Then** the dialog closes, no session is
   deleted, and no row is left in a pending or half-selected state.
3. **Given** the confirmation dialog is open, **When** the administrator confirms the
   deletion, **Then** the session and its saved progress and transcript are permanently
   removed, its row disappears from the table, and the heading's session and story counts
   recompute.
4. **Given** a session whose story has been deleted, **When** the administrator deletes that
   session, **Then** it is removed exactly as any other session is — an orphaned session is
   still deletable.
5. **Given** an administrator test-play session in the list, **When** the administrator
   deletes it, **Then** it is removed on the same terms as a player session.
6. **Given** a deletion that fails (for example a network problem), **When** the administrator
   is returned to the table, **Then** a clear notice explains the session was not deleted and
   the row is still present — no row is removed from the view on the strength of a failed
   request.
7. **Given** a signed-in user who is not an administrator, **When** they attempt the deletion
   directly against the server, **Then** it is refused server-side, independently of whether
   the screen offered them the control.

---

### User Story 3 - A player whose session is deleted lands somewhere sensible (Priority: P1)

A player is part-way through a story when an administrator deletes that very session. The next
thing the player does — takes a turn, saves a checkpoint, refreshes — tells them plainly that
the session has been removed and puts them back on the Home page, where the session is no
longer listed among their games.

The message states that the session has been removed, without naming who removed it: the
application cannot distinguish an administrator's deletion from the player's own deletion in
another tab, and claiming an actor it did not observe would be a fabrication.

**Why this priority**: Deletion is only safe if the player on the other end of it is handled
honestly. Without this, a player would keep typing into a session that no longer exists and
receive a generic error, or see a phantom entry in their games list.

**Independent Test**: Start a player session, delete it as an administrator from the Sessions
page, then act as the player on the play surface and confirm the player is returned to Home
with a message stating the session has been removed, and that the session is absent from their
list of games.

**Acceptance Scenarios**:

1. **Given** a player on the play surface whose session has just been deleted, **When** they
   submit their next instruction, **Then** they are returned to the Home page and shown a
   message stating that this session has been removed.
2. **Given** the same player, **When** they instead refresh the play surface or save a
   checkpoint, **Then** the same return-to-Home-with-a-message outcome occurs — the player is
   not left on a dead screen by whichever action they happened to take.
3. **Given** the player has been returned to Home with that message, **When** they dismiss it,
   **Then** they stay on Home with a working, up-to-date list of their games and can start or
   resume another story normally.
4. **Given** a player whose session was deleted while they were not playing, **When** they next
   open Home, **Then** the deleted session simply does not appear in their list of games, with
   no error, no placeholder row, and no message.
5. **Given** a player who tries to resume the deleted session from a stale Home page (for
   example a tab left open since before the deletion), **When** they select Resume, **Then**
   they receive the same session-removed message rather than a generic failure.

---

### User Story 4 - Bring a stale Sessions list back in sync (Priority: P3)

An administrator who suspects the list is out of date — someone has been playing, or another
administrator has been deleting — refreshes it in place without leaving the screen.

**Why this priority**: A recovery path, consistent with the refresh capability every other
authenticated screen already offers; valuable but not the screen's purpose.

**Independent Test**: Trigger the screen's refresh control and confirm the table and heading
are re-read from the server while the administrator stays on the Sessions screen.

**Acceptance Scenarios**:

1. **Given** the administrator is on Sessions, **When** they use the refresh control, **Then**
   the table and heading are redrawn from the server's current list and the administrator
   remains on the screen.
2. **Given** a refresh that fails, **When** it returns, **Then** the previously loaded table
   stays visible and a clear notice explains the refresh did not succeed — the list is never
   silently replaced with an empty one.

---

### Edge Cases

- What happens when two administrators delete the same session concurrently? → The second
  deletion finds nothing to delete and is reported as an already-removed session, not as an
  unexplained failure; the row leaves the second administrator's table either way.
- What happens when a very long account address or a full session identifier would widen the
  table? → Both wrap within their cells; the table never scrolls horizontally and the Delete
  action is never pushed off-screen.
- What happens to the heading when deleting the last session of a story? → The story count
  drops by one; deleting the last session altogether puts the screen into its empty state.
- What happens if the list cannot be loaded at all? → A clear loading or error state replaces
  the table; no stale or fabricated rows are shown.
- What happens to a player who is mid-turn (their instruction is already being processed) when
  the session is deleted? → The in-flight turn either completes against the pre-deletion state
  or fails; either way the player's following action returns the session-removed outcome, and
  no turn is written back to a deleted session.
- What happens to the story's own cumulative token total when a test-play session is deleted?
  → It is unchanged; story totals are never decremented (see *Scope note: honest data*).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Sessions screen MUST present the fixed, non-scrolling page shell the
  canonical design specifies — nav pinned, only the content area scrolling — and MUST place
  the Sessions nav item in the current-page state.
- **FR-002**: The page heading MUST state the number of sessions and the number of distinct
  stories those sessions belong to, in a single sentence, correctly singularised for counts of
  one, excluding deleted stories from the story count, and recomputing whenever the list
  changes.
- **FR-003**: The sessions table MUST show, per session: the story's title, the full session
  identifier, the session's cumulative token total, the owning account, and a Delete action.
- **FR-004**: A session whose story no longer exists MUST render a visually distinct
  deleted-story label in the Story cell rather than an empty cell, and MUST remain fully
  actionable.
- **FR-005**: Token totals MUST render as thousands-separated, right-aligned, digit-aligned
  numbers, with a session that has recorded no turns showing `0` rather than a blank or a dash
  (026-token-usage FR-018, unchanged).
- **FR-006**: An administrator MUST be able to delete any listed session — real player session
  or administrator test-play session alike. This supersedes 026-token-usage FR-016 (see *Scope
  note*).
- **FR-007**: Deletion MUST always pass through an explicit confirmation step that names the
  session being deleted by a short prefix of its identifier and by its owning account, and
  states that the action cannot be undone. There MUST be no path that deletes a session
  directly from the table row without that confirmation.
- **FR-008**: Confirmed deletion MUST permanently remove the session together with its saved
  progress and its transcript of turns.
- **FR-009**: Deletion MUST NOT decrement any story's cumulative token total and MUST NOT
  remove or alter previously recorded per-call usage telemetry.
- **FR-010**: Deletion MUST be restricted to administrators and MUST be enforced server-side,
  independently of whether the client offered the control.
- **FR-011**: A deleted session MUST NOT appear in the owning player's list of games; it is
  removed from that list with no placeholder, error, or residual entry.
- **FR-012**: When a player acts on a session that has been deleted — taking a turn, saving a
  checkpoint, refreshing the play surface, or resuming it — the system MUST return the player
  to the Home page and show a message stating that the session has been removed. The message
  MUST NOT name who removed it (see User Story 3). Detection on the player's next action is
  sufficient; the system is NOT required to interrupt an idle player (see *Assumptions*).
- **FR-012a**: A removed session MUST be distinguishable from a deleted or unpublished story.
  Today a missing session and a missing story produce the same story-deleted outcome on the
  play surface, which would tell a player their story was deleted when in fact only their
  session was; the two MUST carry distinct outcomes and distinct messages.
- **FR-013**: The session-removed message (FR-012) MUST be dismissible, and dismissing it MUST
  leave the player on a working, current Home page from which they can start or resume another
  story.
- **FR-014**: A failed deletion MUST leave the session present in the table and MUST show a
  clear notice that it was not deleted; the view MUST NOT optimistically remove a row that the
  server did not actually delete.
- **FR-015**: Deleting a session that has already been deleted MUST be reported as an
  already-removed session rather than an unexplained failure, and MUST leave the table
  consistent with the server.
- **FR-016**: The screen MUST offer a refresh action consistent with the refresh capability
  already available on other authenticated screens, re-reading the list without leaving the
  screen; a failed refresh MUST keep the existing table visible behind a clear notice.
- **FR-017**: Long session identifiers and account addresses MUST wrap within their cells; the
  table MUST NOT scroll horizontally and the row's Delete action MUST stay reachable.
- **FR-018**: The empty state MUST replace the table with a short explanatory sentence and set
  the heading to the design's no-sessions wording.
- **FR-019**: A caption beneath the table MUST state what deletion destroys and what it leaves
  behind, worded so that it is true of the records this application actually keeps (see *Scope
  note: honest data*).
- **FR-020**: The screen's visual presentation — layout, type, spacing, table styling, button
  styling, and the confirmation dialog — MUST be built from the project's shared design system
  and its centralized button language, reusing the confirmation-dialog and table patterns the
  People screen already established rather than introducing page-specific equivalents.
- **FR-021**: *Withdrawn.* It required the constitution's **Administrator — sessions** screen
  contract to be amended before this screen ships. Constitution v10.0.0 (issue #340) withdrew
  every screen contract, so there is nothing to amend; this spec is the sole statement of the
  screen's acceptance reference and its delete affordance.

### Key Entities

- **Session**: One run of a story — either a player's play session or an administrator's
  test-play session. Identified by its own identifier, and carrying the story it belongs to,
  the account that owns it, its cumulative token total, its saved progress, and its transcript
  of turns.
- **Sessions view**: The administrator's list of every session in the instance, most recent
  first, from which the heading's session and story counts are derived. Not paginated, sorted,
  or filtered.
- **Session-removed outcome**: What a player receives when they act on a session that no
  longer exists — a distinct, recognisable outcome carrying its own message, separate from the
  existing deleted-story and unpublished-story outcomes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can identify the story, owner, and token cost of any session in
  the instance, and remove it, without leaving the Sessions screen and without any navigation
  beyond the confirmation dialog.
- **SC-002**: No session is ever destroyed by a single click: every deletion in testing
  requires a confirmation step that names the session first.
- **SC-003**: Every element the canonical design places on the Sessions screen is present in
  the position the design gives it — verified element by element against
  `specs/designs/08-admin-sessions-spec.md` and `08-admin-sessions.html` — with the caption's
  wording as the one documented, data-honesty-driven deviation.
- **SC-004**: Across lists of 0, 1, 14, and 50+ sessions, the nav and heading stay in the same
  fixed position and the outer page never scrolls; only the content area does.
- **SC-005**: A player whose session is deleted mid-play reaches the Home page with an
  explanation on their first subsequent action, and never sees a raw error or a phantom entry
  for that session in their list of games.
- **SC-006**: Every existing automated test covering the Sessions list's contents
  (026-token-usage) and the play surface's existing deleted-story and unpublished-story
  handling continues to pass unchanged in what it verifies.

## Assumptions

- **Detection is on the player's next action, not by polling or server push** (FR-012, user
  decision of 2026-09-13). A player sitting idle on a deleted session stays on that screen
  until they act; the application adds no periodic background check and no push channel for
  this, both of which would be new infrastructure against a requirement that does not ask for
  promptness (Principles IV and XII).
- **Both session kinds are deletable** (FR-006, user decision of 2026-09-13). The list already
  mixes player and administrator test-play sessions, and a Delete control that silently did
  nothing on some rows would be worse than none.
- The design's "Token totals stay in the usage record" caption is reworded rather than taken
  literally, because no per-session usage ledger survives the session document (see *Scope
  note: honest data*).
- Row order remains the server's existing order; this feature adds no sorting, filtering,
  pagination, search, transcript inspection, currency cost, or date columns, matching the
  canonical design spec's own stated exclusions (`08-admin-sessions-spec.md` §11).
- Responsive behaviour below desktop width is unspecified for this screen, as for the other
  admin screens, beyond the constitution's own 320px floor and no-horizontal-scroll rules.
- "Refresh" means re-reading the same list from the server, matching what refresh already
  means on every other authenticated screen (019-spa-refresh-button); it is not a new kind of
  sync.
- Deleting a session does not touch the story it belongs to, the player's account, or any
  other session — including other sessions the same player owns for the same story.
</content>
