# Research: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Date**: 2026-09-13

**Feature**: `031-sessions-admin-design-spec`

Every decision below was taken against `origin/main` at `6e7d711`.

---

## Decision 1 — One admin delete endpoint, no client-supplied session kind

**Decision**: `DELETE /api/manage/sessions/{sessionId}`, admin-only, with no discriminator in
the request. `SessionOverviewService.delete_session(session_id)` resolves which kind of session
the id names by attempting the player-session delete first and falling back to the test-play
delete, and raises `SessionNotFoundError` when neither container holds it.

**Rationale**: The list mixes `PlaySession` and `TestPlaySession` rows (FR-006), which live in
two containers (`PLAY_SESSIONS_CONTAINER`, `TEST_PLAY_SESSIONS_CONTAINER`). Sending the row's
`sessionType` back as a parameter would let a client choose which container the server reaches
into — an input to validate for no gain, since the id itself already determines the answer.
`SessionOverviewService` is already the one component that knows about both containers, so
resolution belongs there.

**Alternatives considered**: `?type=player|test` query parameter (rejected: client-chosen
container, and the two would disagree whenever the list is stale); two endpoints, one per kind
(rejected: pushes the same resolution problem into the frontend); a single container query to
learn the type before deleting (rejected: an extra cross-partition read to avoid one cheap
point-read miss).

---

## Decision 2 — Admin deletes are new service methods, not a relaxed owner check

**Decision**: Add `PlaySessionService.delete_session_as_administrator(session_id)` and
`TestPlaySessionService.delete_session_as_administrator(session_id)`. The existing
`delete_player_session(session_id, player_id)` and `delete_session(session_id,
administrator_id)` keep their ownership checks exactly as they are.

**Rationale**: The existing methods enforce "this caller owns this session" and are the only
delete path a player-facing or test-play-facing endpoint may use. Making the owner argument
optional would put a bypass one falsy value away from every existing call site. A separate,
explicitly named method is impossible to reach by accident and makes the authorization story
readable at the call site: it is spelled `as_administrator`, and the only endpoint that calls
it is behind `authorize_admin`.

**Alternatives considered**: an optional `player_id=None` "skip the check" mode (rejected:
turns an authorization boundary into a default argument); deleting straight from
`SessionOverviewService` via `get_container(...).delete_item(...)` (rejected: puts a second,
divergent delete primitive outside the service that owns each entity).

---

## Decision 3 — `session_removed` becomes its own outcome, split from `story_deleted`

**Decision**: Introduce a `session_removed` error code (HTTP 404) and return it wherever a
player's own session is missing. `submit_interaction`, `resume_session` and `get_session` in
`backend/api/game/sessions.py` currently catch `(SessionNotFoundError,
AdventureNotFoundError)` together and answer both with `_story_deleted_response()`; those
handlers are split so `SessionNotFoundError` → `session_removed` and `AdventureNotFoundError`
→ `story_deleted`, unchanged. `create_checkpoint`'s generic `404 not_found` becomes
`session_removed` for the same reason.

**Rationale**: This is a correctness fix the feature forces, not a cosmetic one (spec FR-012a).
Before admin deletion existed, a missing session was essentially unreachable, so folding it in
with a deleted story was harmless. Once an administrator can delete a session under a player,
the current behaviour would tell that player "Story has been deleted. You can no longer
continue this story." about a story that is alive and still listed on their Home page. The
service layer already raises the two exceptions distinctly; only the API layer conflates them.

`DELETE /api/game/sessions/{sessionId}` (the player deleting their own saved game) keeps its
existing `404 not_found`: deleting something already gone is not a bump, and nothing routes a
player anywhere on it.

**Alternatives considered**: reusing `story_deleted` and rewording its message (rejected:
the message would then be wrong for the actual story-deleted case); a 410 Gone (rejected: no
other endpoint in this app distinguishes 410 from 404, and the error code, not the status, is
what every frontend branch already switches on).

---

## Decision 4 — The message names no actor

**Decision**: The player-facing copy is "This session has been removed. You can start this
story again from your home page." — it never says who removed it.

**Rationale**: A 404 on a player's own session has more than one cause: an administrator
deleted it from this screen, or the player deleted it themselves from Home in another tab. The
server observes only that the document is gone. Naming an administrator would be asserting
something unobserved, and would read as an accusation in the case where the player did it to
themselves. Constitution "Readability & interaction requirements" #6 also requires plain, warm,
concrete copy with a next action, which the second sentence supplies.

---

## Decision 5 — The bump is a navigation, not a notice with a button

**Decision**: On `session_removed`, `PlayPage` calls a new `onSessionRemoved` callback rather
than setting a notice; `GamePage` handles it with `navigate("/menu", { state: {
sessionRemoved: … } })`, and `HomePage` reads that route state and renders a dismissible dialog
built from `ConfirmDeleteDialog`'s `.dialog`/`.dialog-backdrop` primitives.

**Rationale**: The existing `story_deleted`/`story_unpublished` notices render in place with a
"Return to your story list" button, and `onExit` lands on `GamePage`'s own setup screen, not on
Home. Issue #335 asks for the player to be *bumped* to the home page with a pop-up, so reusing
the in-place notice pattern would not satisfy it. Route state is how `HomePage` ↔ `GamePage`
already pass one-shot context in both directions (`adventureId`, `resumeSessionId`).

**Alternatives considered**: reusing `onExit(message)` (rejected: lands on the character-setup
screen, not Home); a toast (rejected: the app has no toast primitive, and the design system's
dialog is the existing way to demand acknowledgement); a query parameter (rejected: survives
reload and refires the dialog).

---

## Decision 6 — The dialog is `ConfirmDeleteDialog`, reused as-is

**Decision**: The Sessions screen's delete confirmation renders the existing
`components/Common/ConfirmDeleteDialog.jsx` with a `confirmLabel` of "Delete session" and a
`cancelLabel` of "Keep it", matching `08-admin-sessions-spec.md` §6.

**Rationale**: That component exists precisely because `/code-review high` flagged
`StoryDeleteAction` and `SessionDeleteAction` as near-identical dialog copies; adding a third
copy for this screen would reintroduce the duplication it was extracted to remove
(constitution: "a screen MUST NOT reimplement a control the system already provides").

**Deviation recorded**: the canonical mockup stacks two full-width `.btn-block` buttons
(primary "Delete session" above secondary "Keep it"); `ConfirmDeleteDialog` renders them in a
`.dialog-actions` row. The row form is what the People screen and every other delete in the
product already shows, so the shared component wins over the mockup's per-screen arrangement —
consistency across the product's destructive dialogs matters more than this screen matching a
static file button-for-button. Copy, title, and the "cannot be undone" body follow the mockup.

---

## Decision 7 — Page-scoped stylesheet, matching the established pattern

**Decision**: A new `src/frontend/src/components/Admin/AdminSessions.css` holds this screen's
structural rules (kicker, shell, monospace id cell, numeric column, deleted-story label, table
caption). No new tokens, no new button styles.

**Rationale**: `Home.css`, `Play.css` and `AdminAccounts.css` (030) established this: page
structure in a page-scoped stylesheet, everything visual from `designTokens.css`. The shared
button language landed in `designTokens.css` with 030, so the ghost Delete and the Refresh
control need no new styling at all.

**Note on the shell**: `08-admin-sessions-spec.md` §2 states the Sessions and People screens
"must be indistinguishable in structure". The shell, nav, kicker and heading rules therefore
follow `AdminAccounts.css` rather than being re-derived; only the table-specific rules are new.

---

## Decision 8 — The heading's story count comes from the rows

**Decision**: Count distinct non-deleted story names across the fetched rows, client-side. No
new server field.

**Rationale**: The list response already carries `storyName` per row, with
`DELETED_STORY_LABEL` (`"(deleted story)"`) substituted server-side where the story is gone, so
"distinct stories, deleted excluded" is derivable exactly. `08-admin-sessions-spec.md` §10 says
the same ("Counts in the heading are derived from `sessions`, not sent separately").

**Consequence**: the deleted-story sentinel is a display string the client must also recognise
to exclude it from the count and to render it italic. That coupling already exists (the current
page renders `storyName` verbatim); `data-model.md` records it as the contract it now is.

---

## Decision 9 — Optimistic row removal is not used

**Decision**: The row is removed from the table only after the server confirms the delete
(FR-014). A failure leaves the row in place behind a notice; an already-deleted session
(404) removes the row and says so.

**Rationale**: FR-014 forbids showing a table that disagrees with the server on the strength of
a request that failed. The 404 case is the one exception and is not optimism — the server has
confirmed the session is gone, just not by this call.

---

## Decision 10 — Governance changes ride with this feature

**Decision**: This feature's own PR amends (a) the constitution's **Administrator — sessions**
screen contract and (b) `specs/designs/README.md`, and records `026-token-usage` FR-016 as
superseded in that spec's own file.

**Rationale**: Constitution Governance: "No feature may ship a screen that is not traceable to
a screen contract above or to a documented amendment extending one." The current contract says
"no prototype screen" and "a read-only list", both of which this feature contradicts, so
shipping the screen without the amendment is a blocking inconsistency. The amendment is MINOR
(a screen contract gains a prototype reference and an affordance; nothing is removed or
redefined).

**Blast radius**: touching `.specify/memory/constitution.md` puts this change in the
always-`ultra` review tier (CLAUDE.md *Code review triage*), regardless of diff size.
</content>
