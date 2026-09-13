# Feature Specification: Play Surface Design-Spec Conformance

**Feature Branch**: `029-play-surface-design-spec`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "Implement the play surface UI per GitHub issue #332
(https://github.com/RezaMahmood/llm-dungeon/issues/332). The issue says: 'The main
game page should follow the design spec' and attaches specs/designs/03-play.html
and specs/designs/03-play-spec.md as the canonical reference — a full-viewport,
no-page-scroll play screen with a fixed header, a scrolling transcript pane
(chapter numeral/kicker, THE STORY/YOU turn blocks, ~150-word replies), a fixed
input dock (suggested-action chips + free-text command line + spelling-forgiveness
hint), a fixed 292px status panel (location, goal, chapter progress bar, 'Stuck?
Get a hint', autosave notice), and a pause-and-exit dialog. The existing
PlayPage/StoryPane/StatusPanel/InstructionInput/SuggestedActions/PauseDialog
components (008-core-gameplay-done, 009-save-and-continue) already implement much
of this with inline styles; this feature should bring them into conformance with
the current canonical 03-play-spec.md/03-play.html (chapter header, progress
segment bar, hint disclosure, spelling-forgiveness hint, the header's Refresh
control per 019-spa-refresh-button), using shared CSS classes instead of ad hoc
inline styles where the design system calls for page-scoped structural rules,
without breaking any existing gameplay/save-and-continue/story-delete behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Track chapter and progress while reading the story (Priority: P1)

While playing, a player wants to always know where their character is, what
they're trying to do, and how far through the story they are — without breaking
their reading flow or hunting for the information.

**Why this priority**: This is the core promise of the design spec (issue #332):
the transcript is the only thing that moves, and everything else — including
chapter/progress — stays pinned and visible. Without it the screen still "works"
for gameplay but does not deliver the reading experience the design calls for.

**Independent Test**: Load a play session with an active story that reports
chapter progress, and confirm the transcript shows a chapter identifier at the
top of its scrolling content and the status panel shows the player's location,
goal, and a visual progress indicator — all without any additional click.

**Acceptance Scenarios**:

1. **Given** an active session whose latest turn reports chapter progress (e.g.
   chapter 3 of 5) and a location, **When** the play screen loads, **Then** the
   transcript shows a chapter identifier naming that chapter and location, and the
   status panel shows a progress indicator with 3 of its 5 segments marked
   complete.
2. **Given** a transcript containing many turns, **When** the player scrolls the
   transcript, **Then** the chapter identifier scrolls away with the rest of the
   transcript's earliest content, while the header, input dock, and status panel
   do not move.
3. **Given** a story whose turns carry no chapter/progress information, **When**
   the play screen loads, **Then** no chapter identifier or progress indicator is
   shown, and no placeholder or invented values appear in their place.

---

### User Story 2 - Keep playing despite an imperfect command (Priority: P2)

A player types a command with a likely spelling mistake. They want their move to
still count, with a gentle nudge about what the game thinks they meant — never a
rejection that forces them to retype.

**Why this priority**: Directly named in the design spec as a requirement ("the
game never rejects a move outright for spelling") and is a common source of
frustration in text-driven play; it is lower priority than P1 because it affects
only the subset of turns where a typo actually occurs.

**Independent Test**: Submit a command that closely resembles one of the current
turn's suggested actions but is misspelled, and confirm the move is accepted and
narrated normally while a small suggestion note appears beneath the command line.

**Acceptance Scenarios**:

1. **Given** the player types a command that is a near-miss for a recognized word
   or suggested action, **When** they submit it, **Then** the story responds to
   their move as submitted, and a suggestion note appears offering the closest
   likely word.
2. **Given** the suggestion note is showing, **When** the player submits their
   next move (whether or not they act on the suggestion), **Then** the note
   clears and does not reappear unless the new move is itself flagged.
3. **Given** the player types a command with no likely spelling issue, **When**
   they submit it, **Then** no suggestion note appears.

---

### User Story 3 - Get unstuck without losing your place (Priority: P2)

A player who doesn't know what to do next wants a nudge, available right where
they're already looking, that doesn't take them away from the story.

**Why this priority**: Explicitly required by the design spec's status panel
("Stuck? Get a hint"); ranked alongside spelling forgiveness as a support feature
that improves retention without being core to reading the story.

**Independent Test**: Click "Stuck? Get a hint" in the status panel and confirm
guidance appears in place, with the transcript and input dock unaffected and the
player able to dismiss it and keep playing.

**Acceptance Scenarios**:

1. **Given** the player is on the play screen, **When** they select "Stuck? Get a
   hint", **Then** hint guidance appears within the status panel without
   navigating away from the play screen or interrupting the transcript.
2. **Given** the hint is showing, **When** the player selects the control again,
   **Then** the hint is hidden again.

---

### User Story 4 - Recover a stale play screen without leaving the story (Priority: P3)

A player who suspects their play screen is out of date (e.g. they resumed the
same story in another tab, or a reply seems to be missing) wants to bring it back
in sync without abandoning the session.

**Why this priority**: Extends the refresh capability already available
elsewhere in the app (019-spa-refresh-button) to the play screen's header, for
consistency; ranked last because it is a recovery path rather than everyday
gameplay.

**Independent Test**: Trigger the header's refresh control on the play screen and
confirm the transcript and status panel reload from the session's current
recorded state, while remaining on the same screen.

**Acceptance Scenarios**:

1. **Given** the player is on the play screen, **When** they select the header's
   refresh control, **Then** the transcript and status panel are re-drawn from
   the session's currently recorded state, and the player stays on the play
   screen throughout.
2. **Given** the refresh fails (e.g. a network problem), **When** the player
   retries or waits, **Then** the existing transcript remains visible and a clear
   notice explains the refresh did not succeed, without discarding anything the
   player had already typed.

---

### Edge Cases

- What happens when the active story's turns carry no chapter/progress data?
  → The chapter identifier and progress indicator are both omitted; nothing else
  on the screen changes size or position to compensate.
- What happens with a very long transcript (e.g. ten turns, roughly 1,500 words)?
  → The transcript pane scrolls smoothly and lands on the newest reply after each
  turn; the header, input dock, and status panel do not resize or shift.
- What happens when a turn offers no suggested actions? → The suggested-action
  row is omitted for that turn; the free-text command line remains available
  (existing behavior, unchanged).
- What happens if the player asks for a hint right as the session concludes?
  → The hint control does not block or replace the "story has ended" notice
  already required by existing behavior.
- What happens if the header's refresh fails? → The player sees a notice and
  keeps whatever transcript and typed-but-unsubmitted input they had; nothing is
  lost or silently replaced.
- What happens on a session that has already concluded? → Progress, location,
  and goal continue to reflect the final turn; the hint, spelling-forgiveness,
  and suggested-action controls no longer accept new moves, consistent with
  existing concluded-session handling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The play screen MUST remain a fixed, non-scrolling viewport in
  which only the transcript scrolls; the header, input dock, and status panel
  MUST stay in place regardless of how long the transcript grows.
- **FR-002**: The transcript MUST show a chapter identifier — a chapter number
  and the place that chapter is set in — pinned at the top of its scrolling
  content, whenever the active story reports chapter/progress information for
  the current turn. When no such information is available, no chapter
  identifier is shown.
- **FR-003**: Every turn in the transcript MUST visually distinguish the
  player's own submitted text from the story's narrated reply.
- **FR-004**: The transcript MUST automatically show its newest content — with
  no scrolling required from the player — immediately when the play screen
  loads and again after every new turn is added.
- **FR-005**: The input dock MUST always offer, together, both up to three
  clickable suggested next actions (when the current turn has any) and a
  free-text command field — a player must never be limited to only one of the
  two.
- **FR-006**: When the player's typed command is judged a likely misspelling,
  the system MUST accept and act on the move as submitted, and MUST show a
  small, dismissable suggestion note beneath the command line naming the
  likely intended word — never a rejection or a block on submission.
- **FR-007**: The suggestion note from FR-006 MUST clear after the player's next
  submission and MUST NOT persist across turns for which it does not apply.
- **FR-008**: The status panel MUST always show the player's current location,
  and — whenever the current turn provides them — the player's goal and a
  visual indicator of chapter progress (current chapter of the total).
- **FR-009**: The status panel MUST offer a "get a hint" action that a stuck
  player can use without leaving the play screen, losing their place in the
  transcript, or interrupting an in-progress move.
- **FR-010**: The status panel MUST state, at all times the player is on the
  play screen, that progress is saved automatically after every turn.
- **FR-011**: The play screen's header MUST offer a refresh action — consistent
  with the refresh capability already available on other authenticated screens
  — that re-syncs the play screen against the session's currently recorded
  state without requiring the player to leave the story.
- **FR-012**: A failed refresh (FR-011) MUST leave the player's current
  transcript and any unsubmitted typed input intact, and MUST show a clear
  notice that the refresh did not succeed.
- **FR-013**: Pausing MUST continue to present a confirmation naming where the
  story is saved before the player can exit; there MUST remain no way to leave
  an active session that skips this confirmation.
- **FR-014**: The play screen's visual presentation (spacing, color, type
  sizes, and control styles) MUST be built from the project's shared design
  system rather than one-off values invented specifically for this screen.
- **FR-015**: None of the above MUST change or remove any existing gameplay,
  save/resume, checkpoint, or story-availability (deleted/unpublished) behavior
  already delivered by prior features (008-core-gameplay-done,
  009-save-and-continue, 025-story-delete-done).

### Key Entities

- **Turn**: One exchange in a story's history — the story's narrated reply,
  the player's own input for that turn (absent for the story's opening), the
  player's current location and goal at that point, up to three suggested next
  actions, and (optionally) the story's chapter progress as of that turn.
- **Chapter Progress**: The player's position within the story, expressed as
  the current chapter number out of the story's total chapter count.
- **Spelling Suggestion**: A single likely-intended word offered alongside an
  accepted move that the system judged might be misspelled.
- **Session Status**: Whether the play session is still active or has
  concluded, and — when concluded — the reason the story ended.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player looking at the play screen can state their current
  chapter, location, and goal within a single glance at the status panel, with
  no additional click or navigation, whenever that story provides the
  information.
- **SC-002**: Across transcripts of 1, 2, 5, and 10 turns, the header, input
  dock, and status panel occupy the identical layout in all four cases — only
  the transcript's scroll position differs.
- **SC-003**: A command that is a likely misspelling of a recognized word is
  still acted on 100% of the time on first submission — no player is ever asked
  to retype a move purely because of spelling.
- **SC-004**: A player who believes their play screen is out of date can bring
  it back in sync in a single action, without leaving the story or losing any
  text they had already typed.
- **SC-005**: Every automated regression test covering existing gameplay,
  save-and-continue, and story deletion/unpublish handling continues to pass
  unchanged in what it verifies.

## Assumptions

- The hint's actual guidance text is not specified by the design spec (which
  explicitly places "the hint content itself" out of scope) or by this
  feature; a reasonable, generic message pointing the player back at the
  suggested actions and free-text input satisfies FR-009, consistent with the
  project's implementer design latitude for UI features.
- No new backend capability is assumed to exist purely for spelling detection;
  a reasonable default (comparing the player's submitted text against the
  current turn's own suggested actions and recognized vocabulary) satisfies
  FR-006/FR-007 without requiring a new server-side judgment call the design
  spec does not otherwise describe. If the LLM-driven narrative service is
  later extended to flag suspected misspellings itself, that signal can
  replace the client-side comparison without changing this spec's
  requirements.
- "Refresh" (FR-011/FR-012) re-reads the same session's currently recorded
  turns and status from the server, matching the meaning "refresh" already has
  on every other authenticated screen (019-spa-refresh-button) — it is not a
  new kind of sync and does not restart or replay the story.
- Responsive behavior below desktop width, the hint's own authored content,
  checkpoint-management UI, and end-of-story/end-of-chapter screens remain out
  of scope, matching the canonical design spec's own stated exclusions.
