# Quickstart: Remembering and Showing a Player's Avatar

## Prerequisites

- Backend: Python environment for `src/backend` set up per its existing test instructions.
- Frontend: `npm install` in `src/frontend` (existing setup, unchanged).
- No live Cosmos DB required — all tests below run against mocks/fakes, per Constitution
  Principle I.

## Backend

```bash
cd src/backend
pytest tests/unit/test_stored_avatar_description_service.py
pytest tests/unit/test_play_session_service.py -k stored_avatar
pytest tests/unit/test_game_adventures.py -k avatar
pytest tests/unit/test_game_sessions.py -k avatar
pytest tests/unit/test_admin_stories.py -k avatar
```

**Expected outcomes**:

1. `StoredAvatarDescriptionService.get/store/delete_for_story` round-trip correctly against a
   fake Cosmos container, upserting rather than accumulating for a repeated `(playerId, storyId)`
   pair (FR-005, SC-002).
2. `create_session` stores the validated description on success and never on any of its failure
   paths (adventure not found, lockout, rate-limited, format/relevance rejection) (FR-012).
3. `get_adventure` returns the caller's own stored description for that adventure, `null` when
   none exists, and never another player's (FR-006, FR-007, FR-011, SC-004).
4. `get_session_detail_for_player` includes the session's own `avatarDescription`, `null` for a
   pre-existing session that never had one (FR-001, FR-003, SC-005).
5. `delete_story` cascades to remove every `storedAvatarDescriptions` row for that story, and
   leaves `Story.totalTokens` unchanged (FR-009, FR-009a, SC-003).
6. Deleting a session leaves the player's stored description for that adventure untouched
   (FR-010, SC-003).
7. A stored description that no longer passes validation (rules tightened since it was written)
   is still offered as a prefill, then rejected on submission like any other non-conforming text
   (Edge Cases, FR-008).

## Frontend

```bash
cd src/frontend
npx vitest run tests/components/Play/StatusPanel.test.jsx
npx vitest run tests/integration/game_setup_flow.test.jsx
```

**Expected outcomes**:

1. `StatusPanel` renders the avatar description read-only when provided, and renders no
   empty/broken avatar area when it is absent (Acceptance Scenario 1 & 3 of User Story 1, FR-001,
   FR-003).
2. `GamePage` sends `avatarDescription` (not the stale `characterType`) in `createSession`'s
   request body (Decision 7 — the destructuring-bug fix).
3. `GamePage` prefills the avatar field from `getAdventure`'s `avatarDescription` when one exists,
   leaves it empty when none does, and lets the player edit, replace, or keep it unchanged before
   starting (Acceptance Scenarios 1–4 of User Story 2, FR-006, FR-007).

## Manual check (320 px viewport, longest description)

1. Start a session with the maximum 500-character avatar description.
2. Resize the browser (or devtools device toolbar) to a 320 px viewport width mid-session.
3. Confirm location, goal, and progress all remain visible and reachable, and the description
   does not push them out of view (Acceptance Scenario 2 of User Story 1, FR-002, SC-001).
