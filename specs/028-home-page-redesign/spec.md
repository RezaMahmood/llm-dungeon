# Feature Specification: Player Home Page Redesign

**Feature Branch**: `028-home-page-redesign`

**Created**: 2026-09-12

**Status**: Draft

**Input**: User description: "Player Stories and Sessions Design — GitHub issue #328. The player-facing landing experience should match an attached design spec and mockup (07-home-spec.md / 07-home.html): a full-viewport, no-page-scroll page with a nav bar, a small welcome band, and a two-column body — 'Ready to play' (stories not yet started) on the left and 'In progress' (the player's saved sessions, with Resume and Delete) on the right."

## Canonical UI reference

`specs/designs/07-home-spec.md` and `specs/designs/07-home.html` (vendored from issue #328)
are **canonical for everything a player sees on this page** — layout, copy, states,
responsive behavior and interaction states. This feature's job is to:

1. **Hook existing implementation up to that UI** where the behavior already exists
   (session listing, resume, adventure catalogue, refresh, sign-out, capability gating); and
2. **Build implementation to fit the UI** where it does not yet exist (the story blurb,
   player session deletion, the nav's Home entry and role-suffixed name chip).

Where the canonical design and the constitution genuinely conflict, the conflict is resolved
explicitly — by amending the constitution or recording a justified exception — never by
silently following one and ignoring the other. Two such conflicts were resolved this way
(see Clarifications 2026-09-12b): the mobile scroll contract, and the administrator's route
to the admin story list. Behavior the canonical design does not depict but which exists
today (the access-denied and no-capability states, the unavailable-story session state) is
preserved and styled into the new UI rather than dropped.

## Clarifications

### Session 2026-09-12

- Q: Today the app's only post-login landing hub is `/menu` (a two-button menu), and the actual sessions/catalogue UI lives inside `/game`. How should the new Home design fit into routing? → A: Home replaces `/menu` and absorbs the sessions/catalogue UI that currently lives inside the game-setup flow; the adventure-setup wizard (adventure confirmation → character name → character type) becomes a separate step reached only after choosing Play or Resume from Home.
- Q: `specs/designs/02-story-select.html` is the constitution's current "Adventure select" screen-reference and `06` is already taken by `06-game-setup.html`. Where should the new mockup live? → A: Add it as a new numbered screen, `specs/designs/07-home.html`, leaving `02-story-select.html` in place as historical reference. (The constitution's "Adventure select" screen contract is updated by this feature's plan to point at `07-home.html` as the current acceptance reference, since Home now governs the behavior `02` used to describe — `02` is kept only as prior-art, not as a second live contract.)
- Q: The mockup's Delete-session action has no backend support today. Is building that backend capability in scope? → A: Yes — build it end-to-end: a new capability for a player to delete their own saved session (not the story itself), plus the confirmation UI the mockup specifies.

### Session 2026-09-12b (canonical-UI reconciliation)

- Q: The canonical nav brand reads "LLM Dungeon"; the shipped app and all six existing design references read "Lantern". How far does the rename reach? → A: Rename everywhere — `NavBar`, `TitleBar` and their tests, plus the six existing `specs/designs/*.html` references, their index and README.
- Q: The canonical nav gives administrators only "New story" and "Users", which would leave the admin story list (`/admin`) unreachable from Home and break FR-015/SC-005. → A: Render the canonical two links **and** retain the existing "Admin" link to `/admin` — a deliberate, documented deviation, since the mockup predates the admin story list (a screen the constitution itself records as having no prototype).
- Q: Where does the canonical nav's "My stories" entry point, now that Home absorbs its content? → A: Render it as an inert placeholder following the precedent `NavBar` already sets for "Badges", until a future feature specifies a destination.
- Q: The canonical design mandates page-level scrolling at ≤760px, which the constitution's Layout and scroll contract forbids outright. → A: Amend the constitution's scroll contract to permit page-level scrolling at the mobile breakpoint, in the same edit that updates the screen contract.
- Q: The canonical mockup confirms session deletion with a browser `confirm()`. → A: That is a static-prototype artifact, not canonical UI: the **copy** is canonical, the mechanism is the design system's own dialog primitive (Principle VIII forbids browser-default dialogs; `StoryDeleteAction.jsx` sets the pattern).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player lands on Home and sees where they stand (Priority: P1)

A returning player signs in and is taken directly to a single-screen Home page that shows,
without any further clicks: a personalized welcome, every story they have started and not
finished (as "In progress" sessions they can Resume), and every published story they have not
yet started (as "Ready to play" options they can Play).

**Why this priority**: This is the core value of the redesign — replacing a menu click and a
second screen with one landing page that immediately answers "what am I part-way through, and
what can I start?" Without this, nothing else in the feature has a home to live in.

**Independent Test**: Sign in as a player with a mix of in-progress sessions and un-started
stories; verify both lists render with correct content and counts on first paint, with no
additional navigation required.

**Acceptance Scenarios**:

1. **Given** a player with one saved session and several un-started stories, **When** they
   sign in, **Then** Home shows a welcome band reading "You have one story on the go...",
   one card in "In progress", and the remaining stories listed in "Ready to play".
2. **Given** a player with no saved sessions, **When** they view Home, **Then** the "In
   progress" column shows the zero-state message ("When you open a story it lands here...")
   and every published story appears in "Ready to play".
3. **Given** a player with ten or more items in one column, **When** they view Home, **Then**
   that column scrolls independently while the nav bar and welcome band stay fixed and the
   other column is unaffected.
4. **Given** an administrator account (which also holds player capability), **When** they
   view Home, **Then** they see the same page plus the administrator-only nav links ("New
   story", "Users", "Admin") and a name chip reading "... · Administrator"; nothing else
   differs by role.
5. **Given** an administrator authoring a story, **When** they set its blurb and publish it,
   **Then** that blurb is the sentence shown on the story's "Ready to play" row (FR-016).
6. **Given** an account with no capabilities, or one whose access was denied, **When** they
   reach Home, **Then** they see the "Access Pending" explanation or the access-denied
   screen respectively — never empty story columns (FR-017).

---

### User Story 2 - Player resumes or starts a story in one action (Priority: P1)

From Home, a player clicks "Play" on a ready-to-play story or "Resume" on an in-progress
session and is taken directly into that story at the right point — a new session starting
fresh, a resumed one picking up where they left off.

**Why this priority**: Landing on the right information is only useful if it leads directly
into play; this is the page's entire reason to exist alongside User Story 1.

**Independent Test**: From Home, click Play on an un-started story and confirm a new session
begins; separately, click Resume on an in-progress card and confirm it reopens at the saved
chapter/location rather than restarting the adventure-setup flow.

**Acceptance Scenarios**:

1. **Given** a ready-to-play story row, **When** the player clicks anywhere on the row (or
   its Play control), **Then** they enter the adventure-setup flow for that story (character
   name and type), then begin play.
2. **Given** an in-progress session card, **When** the player clicks anywhere on the card (or
   its Resume control), **Then** they resume that exact session without repeating
   adventure-setup.

---

### User Story 3 - Player deletes a saved session they no longer want (Priority: P2)

A player who wants to abandon their progress on a story (to restart it fresh, or because
they're no longer interested) deletes the saved session from the "In progress" list. The
story itself is unaffected and reappears in "Ready to play".

**Why this priority**: Valuable and explicitly specified, but the page is fully usable
without it (a player can simply ignore an unwanted session) — it does not gate Home's launch
the way Stories 1–2 do.

**Independent Test**: From an in-progress card, trigger Delete, confirm the prompt, and
verify the card disappears, the story reappears in "Ready to play", and no other session is
affected. Attempt the same action a second time for the account's only session and verify the
column falls back to its zero state.

**Acceptance Scenarios**:

1. **Given** an in-progress session card, **When** the player clicks Delete, **Then** a
   confirmation naming the story's title appears before anything is removed.
2. **Given** the confirmation is accepted, **When** the deletion completes, **Then** the
   session is permanently gone, the card is removed from "In progress", and the story appears
   in "Ready to play" (it was excluded from that list only because a session existed).
3. **Given** the confirmation is dismissed, **When** the player closes it, **Then** nothing
   changes.
4. **Given** the deleted session was the player's only one, **When** it is removed, **Then**
   "In progress" falls back to its zero state.
5. **Given** a session belonging to a different player, **When** any player attempts to
   delete it directly (e.g. by replaying a network call), **Then** the deletion is refused —
   a player can only delete their own sessions.

---

### Edge Cases

- A story that was published after the player's last visit appears in "Ready to play" without
  requiring anything beyond the normal page load (no manual refresh required, though the nav's
  existing Refresh control is still available for an explicit re-check).
- A story that is unpublished or deleted while a player has an in-progress session on it:
  behavior is governed by the existing story-deletion/unpublish handling elsewhere in the
  product (e.g. `025-story-delete`) and is unchanged by this feature — Home simply reflects
  whatever the session list already reports.
- Deleting a session while it is mid-request (e.g. double-click) must not delete twice or
  error the page; the second attempt finds nothing to delete, and the UI treats that
  "already gone" answer as success rather than surfacing an error.
- An account holding Administrator but **not** Player capability lands on Home like everyone
  else, but cannot be served either story list (the underlying data is player-scoped). Home
  must explain that in place — never render empty columns or a raw error — while keeping the
  nav's admin destinations fully usable.
- A player with zero published stories available and zero sessions is out of scope (per the
  design spec, the catalogue always has at least one story).
- Very long story titles or blurbs are clamped/truncated per the layout rather than breaking
  the fixed row/card heights that keep the two columns' buttons aligned.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST present a single Home page immediately after sign-in, replacing
  the current post-login menu, containing: a navigation bar, a welcome band, and a two-column
  body ("Ready to play" and "In progress").
- **FR-002**: Home MUST list, in "Ready to play," every published story the signed-in player
  has not started a session on, each showing its genre, duration, title, a short blurb, and
  its reading level, with a Play action.
- **FR-003**: Home MUST list, in "In progress," every saved session belonging to the signed-in
  player that has not been completed, ordered most-recently-played first, each showing the
  story title, current chapter, a preformatted last-played phrase, current location, a
  progress indicator (completed vs. total segments), a Resume action, and a Delete action.
- **FR-004**: A story with an in-progress session for the current player MUST NOT also appear
  in "Ready to play."
- **FR-005**: The welcome band MUST show a contextual greeting and a summary sentence whose
  wording depends on the player's in-progress count (zero / one / many), per the design spec.
- **FR-006**: Clicking Play on a ready-to-play story MUST take the player into that story's
  adventure-setup flow (character name and type) and then into a new session.
- **FR-007**: Clicking Resume on an in-progress session MUST take the player directly back
  into that session at its saved point, without repeating adventure-setup.
- **FR-008**: The system MUST let a player delete their own saved session, independent of the
  story it belongs to, only after an explicit confirmation naming the story's title. The
  confirmation MUST read "Delete your saved session for “{title}”? Your progress will be
  lost." (canonical copy) and MUST be presented in the design system's own dialog, never a
  browser-native one.
- **FR-009**: Deleting a session MUST remove only that saved session; the underlying story
  remains in the catalogue and MUST reappear in "Ready to play" for that player immediately
  afterward.
- **FR-010**: The system MUST reject a request to delete a session that does not belong to the
  requesting player.
- **FR-011**: The navigation bar MUST show the "LLM Dungeon" brand, Home, My stories and
  Badges to every signed-in user, and additionally New story, Users and Admin to
  administrators only; role MUST be the only difference in what a user sees on this page.
  ("Admin", reaching the admin story list, is the one documented addition to the canonical
  nav — see Clarifications 2026-09-12b. "My stories" renders as an inert placeholder until a
  future feature gives it a destination.)
- **FR-011a**: The nav's name chip MUST read `{displayName} · Player` or
  `{displayName} · Administrator` according to the signed-in account's capabilities.
- **FR-012**: Home MUST remain a fixed-viewport page (no page-level scroll) on desktop and
  tablet widths, with the "Ready to play" and "In progress" columns scrolling independently of
  each other and of the nav/welcome bands.
- **FR-013**: On narrow (mobile) viewports, Home MUST collapse to a single scrolling column
  per the design spec's responsive rules, preserving all functionality (Play, Resume, Delete)
  with touch targets at or above 44px.
- **FR-014**: All interactive elements on Home (nav links, Play, Resume, Delete, Refresh,
  Sign out) MUST be fully operable by keyboard alone with a visible focus indicator, and MUST
  NOT convey state by color alone.
- **FR-015**: The system MUST continue to support administrators reaching story-authoring,
  user-management **and the admin story list** from Home's nav bar — no destination reachable
  from today's menu may become unreachable.
- **FR-016**: An administrator MUST be able to author a story's blurb (the short,
  player-facing sentence or two the "Ready to play" row displays) while creating or editing
  that story, and that blurb MUST survive publishing, story export and re-import.
- **FR-017**: Home MUST preserve the two account states the current menu handles: an account
  whose access has been denied sees the access-denied screen, and an account holding no
  capabilities sees the "Access Pending" explanation instead of empty story columns.
- **FR-018**: An in-progress session whose story has been unpublished or deleted MUST remain
  visibly distinguishable on its card, with its Resume action unavailable, preserving the
  behavior the current in-progress list already provides.
- **FR-019**: The application's brand name MUST read "LLM Dungeon" wherever it is displayed,
  replacing the previous "Lantern".
- **FR-020**: The welcome band's kicker MUST describe the player's current local time of day
  (e.g. "WEDNESDAY AFTERNOON"), derived from the viewer's own clock.

### Key Entities

- **Story**: A published adventure in the catalogue — tone (shown to players as its genre),
  estimated duration, title, blurb, reading level. `blurb` is new (FR-016); the rest exist
  today. Exists independently of any player's sessions.
- **Session**: A specific player's saved progress on one story — current chapter, last-played
  time, current location, completed/total progress segments. Deleting a Session never deletes
  its Story.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A returning player with existing progress can identify what to resume and what
  to start next without any click beyond signing in.
- **SC-002**: A player can move from Home into active play (new or resumed) in a single click
  from either list.
- **SC-003**: A player can abandon an unwanted saved session and have the corresponding story
  reappear as startable, without contacting an administrator.
- **SC-004**: The page remains fully usable (no broken layout, no loss of function) at viewport
  widths from 320px through desktop, and with either list holding ten or more items.
- **SC-005**: Administrators experience no functional loss versus the current menu — every
  admin destination reachable today from the menu/nav remains reachable in the same number of
  clicks or fewer.

## Assumptions

- "Home replaces `/menu`" per the resolved clarification: the adventure-setup wizard
  (adventure confirmation, character name, character type) is retained as a separate flow
  reached only after Play/Resume, not merged into Home itself.
- The game-setup flow's own duplicate session/catalogue UI is superseded by Home and is
  removed, leaving that flow to own character setup alone; "My stories" survives in the nav
  as an inert placeholder (FR-011).
- Session deletion is a new backend capability scoped to "a player deletes their own session";
  it does not touch story deletion (already covered by `025-story-delete`) or admin session
  management (`026-token-usage`'s read-only admin sessions list).
- Reading level, duration and progress-segment data already exist on stories and sessions
  (per `004-story-creation`, `008-core-gameplay`, `009-save-and-continue`) and are surfaced
  on Home as-is. The canonical row's "genre" is rendered from the story's existing `tone`
  field — the same value under a player-facing name, not a new one. The **blurb** is the one
  genuinely new piece of story metadata this feature adds (FR-016), because the canonical UI
  requires it and no equivalent field exists.
- Visual design and copy follow `specs/designs/07-home.html` and the attached design spec
  exactly, using the existing vendored `specs/designs/styles.css` design tokens; no new design
  tokens are introduced.
