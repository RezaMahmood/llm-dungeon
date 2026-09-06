# Implementation Plan: Save and Continue

**Branch**: `009-save-and-continue` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-save-and-continue/spec.md`

## Summary

`008-core-gameplay` already persists a `PlaySession` after every turn and already owns
single-active-session semantics, but it ships no way to *read a session back* — the play
surface only ever holds turns it saw created in the same browser session. This feature
closes that gap and layers the deliberate save affordances on top: a "Stories in progress"
list of the player's own unconcluded games, resuming one with its full narrative history
restored, an explicit checkpoint save that confirms visibly, and a prompt to save when the
player signs out with a game in progress.

The spec's clarifications settled what "saving" means here: because progress is already
autosaved every turn, an explicit save records a **labelled, timestamped checkpoint
marker** — history, not a rewind point — and a player's resumable progress is identical
whether they accept or decline the sign-out prompt. The only real difference the prompt
makes is whether a marker is recorded.

Technical approach: one new embedded structure, `CheckpointMarker`, appended to a new
`checkpoints` array on the existing `PlaySession` document — no new Cosmos container, no
Terraform change, no migration (a missing `checkpoints` key loads as `[]`). Three new
endpoints on the existing `game/sessions` route family: `GET /api/game/sessions` (the
player's own in-progress games, projected without `turns`), `GET /api/game/sessions/{id}`
(one session in full, for rehydration), and `POST /api/game/sessions/{id}/checkpoints`
(record a marker, label generated server-side from the latest turn's location). `008`'s
three existing endpoints are untouched, including `resume`'s `409 already_active` — the
client decides whether a resume call is needed at all from the `isActiveForPlayer` flag the
list already returns. On the frontend, the continue list is added above the adventure
picker on `/game` (completing `02-story-select.html`'s two-section screen), `PlayPage`
gains a turn history and publishes a save handler through the existing `PlayTitleContext`
so `TitleBar`'s already-rendered "Save a checkpoint" button stops being inert, and `NavBar`'s
sign-out grows a save prompt gated on whether the player actually has an active game. See
[research.md](./research.md) for the decisions behind each of these.

## Technical Context

**Language/Version**: Python 3.11 (backend, Azure Functions), JavaScript/JSX + React 19
(frontend, post-`#251` upgrade)

**Primary Dependencies**: `azure-functions`, existing `CosmosService`/`StoryService`/
`PlaySessionService`/`AccountProvisioningService` (backend, all reused, none replaced);
React Router, MSAL 5, existing design-token layer (`specs/designs/styles.css`) (frontend).
**No new dependency in either tier, and no LLM call anywhere in this feature.**

**Storage**: Azure Cosmos DB — the existing `playSessions` container only, gaining one
embedded `checkpoints` array per document. Reads the existing `stories` container via
`StoryService` for adventure names. No new container, no schema migration.

**Testing**: `pytest` (backend unit + integration, extending
`tests/unit/test_play_session_service.py`, `tests/unit/test_models.py`, and a new
`tests/integration/test_saved_games_endpoint.py`), Vitest/RTL (frontend, extending
`tests/Play/`, `tests/components/`, and a new `tests/integration/save_and_continue.test.jsx`)

**Target Platform**: Azure Functions (backend), browser SPA served as a static web app
(frontend)

**Performance Goals**: No stated target. The list endpoint is one cross-partition query on
`playerId` — the same shape `_deactivate_other_active_sessions` already issues — plus one
point read per *distinct* adventure; the checkpoint write is one conditional document
write. Nothing here calls the LLM, so no turn-latency budget applies.

**Constraints**: Ownership (`playerId == authenticated user`) is enforced server-side on
all three endpoints before any session content is revealed, per Principle II — the client
is never trusted to filter its own list. A checkpoint write must never clobber a turn
that landed concurrently (ETag `if-match`, one retry), and a failed checkpoint must never
block, delay, or reverse a player's sign-out or return to the stories screen (FR-006a).
The sign-out control exists only in `NavBar`, which `022-persistent-nav-redesign` removed
from the play surface and from `/game`, so the save prompt fires from `/menu` and the admin
screens and is gated on the server's own active-game flag rather than on which screen is
mounted (research.md Decision 6; recorded as an assumption in spec.md).

**Terminology**: the **stories screen** is the route `/game` — the player's in-progress
games (this feature) above the adventures they can start (`006`). `/menu` is the capability
chooser, not the stories screen, despite the nav bar labelling its link "My stories"; that
label mismatch predates this feature (`022-persistent-nav-redesign`) and is out of scope
here. spec.md, tasks.md, and quickstart.md all use "stories screen" for this route.

**Scale/Scope**: Three new backend endpoints on an existing route family, one new embedded
model structure, three new service methods, one new frontend list component, one new
sign-out prompt component, and extensions to `PlayPage`/`TitleBar`/`PlayTitleContext`/
`NavBar`/`GamePage`/`gameService`. No new Azure resource, no new container, no
infrastructure change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing**: FR-007 enumerates the outcomes that must each be
  covered, and quickstart.md's nine scenarios map onto them one-for-one: continue with
  games present, continue with none, cross-player isolation (403/empty list), explicit
  save, no-op double save, resume-never-rewinds, resuming while another game is active,
  resuming the already-active game, sign-out-with-save, sign-out-declined, sign-out with no
  active game, concluded-game 409, and failed-checkpoint non-blocking behaviour. All run
  locally against the Cosmos emulator/stubs — no live Azure dependency. PASS.
- **II. Secure-by-Default Access**: All three endpoints go through the existing
  `authorize_player` middleware unchanged. The list query filters on `playerId` **in the
  query itself**, server-side; the detail read and the checkpoint write both compare
  `session.playerId` to the authenticated `oid` and return the same generic
  `forbidden_access_not_granted()` body `submit_interaction` already uses — never a
  different status or message that would confirm an id exists. The sign-out prompt's "is a
  game in progress?" answer comes from the server's own `isActiveForPlayer` flag, not from
  client state. PASS.
- **III. Defined Technology Stack**: Python/Azure Functions backend, ReactJS frontend, no
  new dependency in either. PASS.
- **IV. Simplicity Over Premature Scale**: Markers are an embedded array on a document that
  already exists rather than a container, a document type, or a service of their own; the
  continue list reuses the cross-partition query shape already in
  `play_session_service.py`; the sign-out check reuses the list endpoint rather than adding
  a fourth; resume idempotency is a client-side branch rather than a rewrite of a shipped
  contract; no pagination, marker cap, or rate limit is built ahead of a stated need
  (research.md Decisions 1, 3, 5, 6). PASS.
- **V. Continuous Integration Gate**: New and extended tests run in the existing CI
  pipeline; no CI configuration change. PASS.
- **VI. Observability & AI Cost Transparency**: This feature makes **no LLM call**, so there
  is no new AI cost surface. The three endpoints are ordinary traced HTTP handlers under the
  existing `observability/setup.py` instrumentation, same as `game/adventures`. PASS.
- **VII. Zero-Trust Azure Resource Communication**: No new Azure resource and no new
  container — the same Managed-Identity-authenticated `CosmosService` and existing
  account-level role assignment cover every read and write here. No new role assignment.
  PASS.
- **VIII. UI Design System & Accessibility Compliance**: The continue list is built to
  `specs/designs/02-story-select.html`'s "stories in progress" rows (ordinal, title,
  "chapter · last played · location" meta line, progress bars, Resume action) using only
  the vendored token layer and shared component classes. The play surface gains **no new
  chrome**: the "Save a checkpoint" button already exists in `TitleBar` per
  `03-play.html` and is simply given the handler it has always lacked, so FR-016's "no path
  exits without the pause confirmation" is preserved. The sign-out prompt is a standard
  `dialog`/`dialog-backdrop` modal matching `PauseDialog`, keyboard-operable with a visible
  focus indicator. Which game is the active one is conveyed with **text plus** styling, never
  colour alone. Save confirmations and failure notices use `role="status"`/`role="alert"` so
  they reach assistive technology. PASS.
- **IX. Playtesting-Driven Quality**: Non-blocking under the current constitution —
  automated tests are the completion gate; any playtesting task in `tasks.md` is
  informational. PASS.
- **X. PII Protection by Design**: A `CheckpointMarker` stores an in-fiction location
  string, a turn number, and a timestamp — no PII. The list and detail reads project only
  fields `PlaySession` already holds (opaque Entra `oid` as `playerId`, player-chosen
  fictional `characterName`, narrative text), adding none. PASS.
- **XI. Implementer Design Latitude**: No pre-implementation sign-off required; the existing
  `02-story-select.html` and `03-play.html` mockups are themselves the acceptance
  reference, and this feature introduces no undesigned surface beyond the sign-out prompt,
  which follows `PauseDialog`'s established dialog pattern. PASS.
- **XII. Right-Sized Scope**: No new environment, container, identity pattern, or scaling
  mechanism. The one genuinely new thing is an embedded three-field array. PASS.
- **XIII. AI Agent Division of Labor**: Standard — local work, then `gh pr create` labelled
  `AI Generated` and `Claude`, no auto-merge, no issue closure. PASS (process, not design).

**Result**: No unjustified violations. No Complexity Tracking entries needed.

**Post-Phase-1 re-check**: The Phase 1 artifacts introduce no container, no dependency, no
LLM call, no role assignment, and no new play-surface chrome — every gate above holds
unchanged after design. The one design decision worth restating against a principle is
Decision 7 (a failed checkpoint never blocks departure): it is what FR-006a requires, and
its accepted limitation — the failure notice is only briefly visible before the sign-out
redirect navigates away — is documented in research.md rather than papered over.

## Project Structure

### Documentation (this feature)

```text
specs/009-save-and-continue/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api.md           # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md  # Spec quality checklist (/speckit-specify command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/backend/
├── api/
│   └── game/
│       └── sessions.py                 # EXTENDED — list_sessions (GET /api/game/sessions),
│                                       #   get_session (GET .../{sessionId}),
│                                       #   create_checkpoint (POST .../{sessionId}/checkpoints)
├── models/
│   └── play_session.py                 # EXTENDED — CheckpointMarker; PlaySession.checkpoints
│                                       #   (defaults to [], absent-key tolerant in from_dict)
├── services/
│   └── play_session_service.py         # EXTENDED — list_player_sessions (own active sessions,
│                                       #   newest first, adventure names batched by distinct id),
│                                       #   get_session_for_player (ownership-checked read),
│                                       #   record_checkpoint (ETag write, one retry)
├── function_app.py                     # EXTENDED — 3 new routes on the game/sessions family
└── tests/
    ├── unit/
    │   ├── test_models.py              # EXTENDED — CheckpointMarker round-trip; legacy
    │   │                               #   document with no `checkpoints` key loads as []
    │   └── test_play_session_service.py # EXTENDED — listing scope/order/name resolution,
    │                                    #   ownership, checkpoint append + no-op double save,
    │                                    #   concluded rejection, ETag retry, turns untouched
    └── integration/
        └── test_saved_games_endpoint.py # NEW — the three endpoints end to end, incl. 403 for
                                         #   another player, empty list, 409 session_concluded

src/frontend/
├── src/
│   ├── components/
│   │   ├── GameSetup/
│   │   │   ├── StoriesInProgress.jsx   # NEW — the 02-story-select.html "stories in progress"
│   │   │   │                           #   rows, active-game marker, empty state (FR-001, FR-002)
│   │   │   └── SavedGameRow.jsx        # NEW — one row: title, chapter/last-played/location,
│   │   │                               #   progress bars, Resume action
│   │   └── Layout/
│   │       ├── LogoutSavePrompt.jsx    # NEW — save-before-sign-out dialog (FR-004, FR-005)
│   │       ├── NavBar.jsx              # EXTENDED — sign-out routes through the prompt when the
│   │       │                           #   player has an active game
│   │       └── TitleBar.jsx            # EXTENDED — onSaveCheckpoint falls back to the published
│   │                                   #   context value, as onPauseExit already does
│   ├── context/
│   │   └── PlayTitleContext.jsx        # EXTENDED — carries onSaveCheckpoint alongside
│   │                                   #   storyTitle/onPauseExit
│   ├── pages/
│   │   ├── GamePage.jsx                # EXTENDED — renders StoriesInProgress above the adventure
│   │   │                               #   picker; resume handoff into PlayPage (FR-001a)
│   │   └── PlayPage.jsx                # EXTENDED — initialTurns (history) instead of a single
│   │                                   #   initialNarrative; publishes onSaveCheckpoint; save
│   │                                   #   confirmation and failure notices (FR-003, FR-006a)
│   └── services/
│       └── gameService.js              # EXTENDED — listSavedGames, getSession, saveCheckpoint
└── tests/
    ├── Play/
    │   └── PlayPage.test.jsx           # EXTENDED — resumed history renders; save confirmation;
    │                                   #   failed save notice leaves the game playable
    ├── components/
    │   ├── GameSetup/
    │   │   └── StoriesInProgress.test.jsx  # NEW — rows, ordering, active marker, empty state
    │   ├── LogoutSavePrompt.test.jsx   # NEW — accept/decline/no-prompt, failure non-blocking
    │   ├── NavBar.test.jsx             # EXTENDED — prompt shown only with an active game
    │   └── TitleBar.test.jsx           # EXTENDED — published onSaveCheckpoint is invoked
    └── integration/
        └── save_and_continue.test.jsx  # NEW — list → resume → play → save → sign-out round trip
```

**Structure Decision**: The existing web-application split (`src/backend`, `src/frontend`)
is reused unchanged, and so is every file this feature touches — there is no new module
boundary here. Backend work lands as additional handlers in the existing
`api/game/sessions.py` and additional methods on the existing `PlaySessionService`, because
all three endpoints operate on the same `playSessions` documents that service already owns;
splitting them into a parallel "saved games" service would fragment `PlaySession` writes
across two owners and put the checkpoint write outside the ETag discipline the rest of that
service maintains. Frontend work follows the same file-per-concern pattern as `008`:
presentational pieces under `components/`, data access in `services/gameService.js`, and
page-level composition in `GamePage`/`PlayPage`. `infrastructure/terraform/` is **not**
touched — the embedded `checkpoints` array needs no new container (research.md Decision 1).

## Delivery Sequence

Work is **strictly sequential**: Setup → Foundational → User Story 1 → User Story 2 →
Polish. [tasks.md](./tasks.md) carries the authoritative task-level order; this section
records why the phases are ordered that way, so the two documents cannot drift.

1. **Setup** — establish a green baseline so later failures are attributable.
2. **Foundational** — the model change plus `GET /api/game/sessions`. This blocks **both**
   stories: US1 has nothing to list without it, and US2's sign-out prompt uses the same
   endpoint to decide whether a game is in progress (research.md Decision 6).
3. **User Story 1 (P1)** — the continue screen and session rehydration. Shippable alone,
   and the MVP: it closes the gap where `008` persists a session but can never read one
   back.
4. **User Story 2 (P2)** — checkpoints and the sign-out prompt.
5. **Polish** — accessibility, design-system conformance, design README, full validation.

**The two stories are sequential, not parallel.** They have no logical dependency — US2's
endpoints and prompt function whether or not the continue screen exists, and its
Independent Test reads the API directly rather than through US1's screen — but they modify
eight of the same files (`play_session_service.py`, `api/game/sessions.py`,
`function_app.py`, `gameService.js`, and four shared test files; the full table is in
tasks.md). Building them concurrently produces eight merge conflicts rather than a
speed-up, so US1 goes first on priority order and stops at a demoable MVP.

Within each phase the order is: tests (written first, failing) → models → services →
endpoints → routes → client → components → page wiring.

## Complexity Tracking

*No Constitution Check violations requiring justification — table intentionally omitted.*
