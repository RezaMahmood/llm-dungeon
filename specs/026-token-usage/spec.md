# Feature Specification: Story Token Usage Tracking

**Feature Branch**: `026-token-usage`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "I want to track the number of LLM tokens used during the process of story creation. When I look at the stories list, I want another column that shows the total number of tokens that have been used in the creation of that story. It should be a cumulative total, including everything from the very start of the creation process. At present there is a Published Status together with a last published date. The last published date should be moved into an on-hover text box so that when you hover over the Published text it tells you the last published date - this should then make space for that token count column which just shows a number."

## Clarifications

### Session 2026-09-11

- Q: Should tokens used during real player gameplay sessions now count toward a story's cumulative token total (the stories-list column), or stay excluded from that total and appear only on the new Sessions page? → A: Keep excluded — the story's cumulative total remains authoring-lifecycle only (creation, edits, admin test plays); real player gameplay usage is tracked per-session on the Sessions page instead, and is never rolled into `Story.totalTokens`.
- Q: For a test-play session row on the Sessions page, whose email should show in the "player email" column, since test sessions are run by an admin rather than an end player? → A: The tester's own email — the column represents whoever was at the controls for that session, whether a real player or an admin running a test play.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See cumulative token usage for each story (Priority: P1)

As an admin reviewing the stories list, I want to see the total number of LLM tokens spent building each story, so I can understand and compare the AI cost of each story at a glance without leaving the list.

**Why this priority**: This is the core value the feature request is for — a visible, per-story running total. Without it, nothing else in this feature has a purpose.

**Independent Test**: Open the stories list and confirm every row shows a numeric token total; verify the number for one story against the sum of the LLM calls known to have been made for it.

**Acceptance Scenarios**:

1. **Given** a story that has gone through initial creation, **When** an admin opens the stories list, **Then** that story's row shows a single number representing its total tokens used so far.
2. **Given** a story that predates this feature or has never triggered an LLM call, **When** an admin opens the stories list, **Then** that story's row shows a token count of 0 rather than an error or blank cell.
3. **Given** a story currently showing a token total of N, **When** an admin performs an action on that story that makes another LLM call (e.g. regenerating content during editing, or an admin test play), **Then** the story's token total subsequently shown is greater than N by the amount of that call's usage.

---

### User Story 2 - Find a story's last published date without cluttering the list (Priority: P2)

As an admin, I want the last-published date to still be available for a story, but tucked behind a hover rather than always shown, so the list has room for the new token column without getting more crowded.

**Why this priority**: This is what makes room for User Story 1's column, and is explicitly requested, but it's a layout/decluttering change rather than new information — nothing is lost, just relocated.

**Independent Test**: Hover over the Published indicator for a published story and confirm the last published date appears; confirm it is not shown as permanent inline text.

**Acceptance Scenarios**:

1. **Given** a story that has been published at least once, **When** an admin hovers over that story's "Published" status indicator, **Then** a tooltip appears showing the date it was last published.
2. **Given** a story that has been published at least once, **When** an admin is not hovering over the status indicator, **Then** the last published date is not shown as visible inline text on the list.
3. **Given** a story that has never been published, **When** an admin hovers over its status indicator, **Then** no last-published date is shown (since none exists), and no error occurs.

---

### User Story 3 - Token totals stay accurate across the whole story lifecycle (Priority: P3)

As an admin, I want a story's token total to reflect everything spent on it — not just its first draft — so the number is trustworthy as the story is edited, regenerated, or test played over time.

**Why this priority**: This is what makes the column in User Story 1 a true cumulative total rather than a one-time snapshot; it matters most once stories are actively maintained past their first creation, so it can follow the first two stories into place.

**Independent Test**: Take a story with an existing token total, perform an admin edit that triggers content regeneration and a test play, then confirm the list's total increased to include both.

**Acceptance Scenarios**:

1. **Given** a story that has already been created and published, **When** an admin edits it in a way that triggers new AI-generated content, **Then** the tokens used by that regeneration are added to the story's existing total, not tracked separately or overwritten.
2. **Given** a story, **When** an admin test-plays it (triggering gameplay-simulation LLM calls as part of reviewing the story), **Then** those tokens are also added to the story's total.

---

### User Story 4 - Review token usage per gameplay session (Priority: P2)

As an admin, I want a dedicated page listing every gameplay session — both real player playthroughs and admin test plays — with the story it belongs to, a session identifier, the total tokens that session used, and the email of whoever ran it, so I can see where AI usage during actual play is going, separately from the cost of creating each story.

**Why this priority**: This delivers the same kind of visibility as User Story 1, for a distinct and equally real cost center (gameplay, not authoring). It doesn't block or depend on the token-count column, so it can ship right after it.

**Independent Test**: Play through (or test-play) a story for a few turns, then open the new Sessions page and confirm a row exists for that session showing the story name, a session identifier, a non-zero total token count, and the email of the person who played it.

**Acceptance Scenarios**:

1. **Given** a player has played several turns of a published story, **When** an admin opens the Sessions page, **Then** a row for that session shows the story's name, a session identifier, the cumulative tokens used across that session's turns so far, and the player's email address.
2. **Given** an admin has run a test play of a story, **When** that admin opens the Sessions page, **Then** a row for that test session shows the story's name, a session identifier, the cumulative tokens used in that test session, and the email of the admin who ran it.
3. **Given** the Sessions page is open, **When** an admin looks at the navigation menu, **Then** "Sessions" appears as its own item alongside the existing admin menu items (e.g. Stories, People).
4. **Given** the Sessions page, **When** an admin views it, **Then** there is no way to edit, delete, or otherwise modify a session or its data from that page — it is read-only.

---

### Edge Cases

- A story created before this feature existed has no historical per-call token data — its total MUST display as 0 (not blank, not an error), since there's nothing to backfill.
- An LLM call made for a story fails or is aborted partway through — only tokens actually consumed/billed by the call are counted; a call that produced no response contributes 0.
- A story is deleted — its token total is deleted along with it; no orphaned totals need to be shown anywhere.
- Two admins act on the same story at the same time (e.g. one edits while another test-plays) — both calls' tokens MUST still be added to the total; neither update should overwrite the other.
- A story's token total grows very large over its lifetime — the displayed number MUST remain readable (e.g. with thousands separators) rather than becoming an unbroken string of digits.
- A story has been unpublished after having been published before — hovering still shows the (past) last published date, since that fact doesn't change when the story is unpublished.
- A gameplay session is still in progress (not yet ended) — it still appears on the Sessions page, with its running total reflecting only the turns taken so far.
- A session's turns produce zero billable tokens (e.g. a turn that failed before the LLM responded) — that turn contributes 0 to the session's running total rather than breaking it.
- A story referenced by a session has since been deleted — the session row still appears (sessions are not deleted along with the story), showing the story's last-known name rather than disappearing or erroring.
- A player or admin who ran a session is no longer a provisioned account (e.g. their access was later revoked) — the session row still appears, with the email shown as it was on record at the time, or a clear placeholder if no record can be found.
- The Sessions page has many rows over time — admins can still find what they need without the page becoming unusably slow to load (no specific volume target is set; see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track token usage for every LLM call made in the course of a story's authoring lifecycle: its initial creation flow, any subsequent content edits or regenerations, and admin test plays of that story.
- **FR-002**: System MUST maintain a single cumulative token total per story that accumulates across every tracked call for the life of that story, starting from its very first LLM call.
- **FR-003**: The stories list MUST display the cumulative token total for each story as a plain number, in a column of its own.
- **FR-004**: A story with no tracked LLM usage (created before this feature existed, or never triggering an LLM call) MUST show a token total of 0, never a blank cell or an error.
- **FR-005**: The stories list MUST NOT display the last-published date as permanently visible inline text.
- **FR-006**: The stories list MUST reveal a published story's last-published date when an admin hovers over that story's Published status indicator.
- **FR-007**: For a story that has never been published, hovering over its status indicator MUST NOT show a fabricated or blank date, and MUST NOT produce an error.
- **FR-008**: A story's token total MUST increase to reflect a new LLM call as soon as that call completes and its usage is known, so the list reflects current usage the next time it is viewed.
- **FR-009**: The token total shown MUST only include LLM calls attributable to that specific story; usage from other stories' creation, editing, or test plays MUST NOT be included.
- **FR-010**: Large token totals MUST be displayed in a readable format (e.g. grouped with thousands separators) rather than as an unformatted string of digits.
- **FR-011**: Ongoing gameplay LLM usage generated by end players playing a published story is out of scope for this per-story creation total (see Assumptions); this feature MUST NOT be interpreted as replacing the project's existing aggregate AI-spend telemetry/dashboards. Player and admin test-play gameplay usage is tracked instead per FR-012 through FR-018 below, and MUST NOT be added into the story's cumulative creation total from FR-002.
- **FR-012**: System MUST record the number of tokens used by each individual gameplay turn (one LLM response produced from one player or tester input), for both real player sessions and admin test-play sessions.
- **FR-013**: The per-turn token count MUST be persisted against that turn, but is not required to be shown anywhere in the admin UI.
- **FR-014**: System MUST maintain a running total of tokens used across an entire gameplay session (player or test-play), updated as each new turn's tokens are recorded.
- **FR-015**: System MUST provide a Sessions page listing every gameplay session — both real player sessions and admin test-play sessions — with, for each session: the name of the story it belongs to, a session identifier, its total token count, and the email address of whoever played it (the real player, or the admin who ran a test play).
- **FR-016**: The Sessions page MUST be read-only: it MUST NOT provide any way to create, edit, or delete a session or its data.
- **FR-017**: The Sessions page MUST be reachable as its own item in the existing admin navigation menu, alongside the existing menu items.
- **FR-018**: A gameplay session with no recorded turns yet (e.g. just started) MUST show a total token count of 0 on the Sessions page, not a blank cell or an error.

### Key Entities

- **Story**: The existing record representing an authored adventure. Gains one new attribute — its cumulative token total — that accumulates over the story's authoring lifecycle and is shown in the stories list. This total is distinct from, and does not include, any gameplay session's token usage.
- **Story LLM Usage**: The token cost (already produced by each existing LLM call made in the course of authoring a story) that contributes to that story's cumulative total. Not a new user-facing concept — this spec adds attribution of that existing per-call usage to a specific story's running total.
- **Gameplay Session**: A single playthrough of a story, either by a real player or by an admin running a test play. Gains a running cumulative token total, built up as its turns occur, and is what the new Sessions page lists — showing the story it belongs to, a session identifier, its token total, and the email of whoever ran it.
- **Turn**: One exchange within a gameplay session — the LLM's output produced in response to one player or tester input. Gains a token count of its own, which feeds the session's running total but is not itself shown in the UI.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can see any story's cumulative token usage directly from the stories list, with no additional clicks or navigation.
- **SC-002**: An admin can still learn a story's last-published date within a single hover interaction, with no loss of information compared to today.
- **SC-003**: After any admin action that triggers new AI-generated content for a story (an edit/regeneration or a test play), that story's token total visibly reflects the increase the next time the list is viewed.
- **SC-004**: The stories list communicates both the token total and the published state (with its date on hover) without adding any new always-visible column beyond the one token-count column.
- **SC-005**: An admin can find the token total and the associated player/tester email for any gameplay session — real or test — from a single new page, without cross-referencing any other page or system.
- **SC-006**: A session's displayed token total visibly reflects a newly completed turn the next time the Sessions page is viewed, with no missing or double-counted turns.

## Assumptions

- The cumulative token total is a running counter attributed to the story record itself (built up as calls happen), not a number computed on the fly from telemetry each time the list is viewed — this keeps the list fast and matches how the project already separates per-story data from aggregate telemetry dashboards.
- "The process of story creation" is read to include the full authoring lifecycle an admin controls for a given story: its initial creation flow, later content edits/regenerations, and admin test plays — not just the first draft.
- Ongoing gameplay by end players on an already-published story is a distinct, ongoing operational cost (already served by the project's existing aggregate AI-spend telemetry) rather than part of a story's one-time-per-edit "creation" cost, and is therefore excluded from this per-story total.
- The displayed number is a simple total token count; it does not need to show a cost figure or an input/output breakdown in the list view — that level of detail remains available through existing aggregate telemetry.
- Stories that existed before this feature shipped have no historical per-call data to reconstruct, so their total starts at 0 going forward rather than being backfilled.
- The hover behavior for the Published status replaces the previously always-visible last-published date; it does not need to show anything for a story that has never been published beyond the existing "Unpublished" indication.
- A gameplay session's running token total is likewise a persisted counter built up turn by turn, not computed live from telemetry, for the same reasons as the story total.
- "Player sessions" and "test sessions" refer to real end-player playthroughs and admin test plays respectively — the same distinction the product already draws elsewhere (e.g. a story's last-tested-at marker) — and both are shown together on one Sessions page rather than two separate pages.
- The email shown per session is sourced from the same provisioned-account records the rest of the admin app already uses to resolve an identity to an email address; a session run by someone no longer provisioned still displays using the identity on record at the time, rather than being hidden.
- The Sessions page is available to any admin who can already reach the existing admin pages (Stories, People) — no additional, narrower permission tier is introduced for it.
- No pagination, filtering, or sorting behavior is prescribed for the Sessions page beyond showing all sessions; the project's simplicity principle means this is added later only if a real usability need emerges, not preemptively.
- The email address surfaced on this admin-only, access-controlled page is an explicit, spec-required exception to the general rule against exposing user-identifying data in telemetry or UI surfaces — it is not general-purpose logging.
