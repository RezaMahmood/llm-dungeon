# Quickstart: Save and Continue

**Feature**: 009-save-and-continue | **Date**: 2026-09-06

Validates continuing a saved game (User Story 1) and saving/returning home, including the
sign-out prompt (User Story 2), end to end. See [contracts/api.md](./contracts/api.md) for
exact request/response shapes and [data-model.md](./data-model.md) for the
`checkpoints` field and the two read shapes referenced below.

## Prerequisites

- Local backend running (`func start` or the repo's standard local-dev command) against the
  Cosmos DB emulator, with the `playSessions` container `008-core-gameplay` already
  provisions. **No new container is needed for this feature.**
- At least two published `Story` documents (so a player can hold two in-progress games on
  different adventures — spec Edge Case 4).
- A valid player bearer token, plus a **second** player's token for the ownership checks
  (local automation identities per Constitution Principle II).
- Local frontend running (`npm run dev` in `src/frontend`) for the UI scenarios.

## Scenario 1 — Continue with saved games present (User Story 1, FR-001)

1. As player A, `POST /api/game/sessions` against adventure X, then submit two
   interactions. **Expect**: 201 then two 200s (`008` behaviour, unchanged).
2. `GET /api/game/sessions`. **Expect**: 200, exactly one row, carrying `adventureName`,
   `characterName`, `locationLabel`, `turnCount: 3`, `isActiveForPlayer: true`,
   `checkpointCount: 0`, and **no** `turns` array.
3. As player B, `GET /api/game/sessions`. **Expect**: 200 with `sessions: []` — player A's
   game is never visible to another player (SC-002).
4. As player B, `GET /api/game/sessions/{A's sessionId}`. **Expect**: 403 with the generic
   access-not-granted body — not a 404, and no session content.
5. As player A, `GET /api/game/sessions/{sessionId}`. **Expect**: 200 with all three turns
   in `turns`, oldest first, matching what was played.
6. In the browser: sign in as player A and open the **stories screen** (`/game`).
   **Expect**: a "Stories in progress" section above "01 — Choose an adventure", separated
   from it by a visible divider, listing
   the game with its adventure title, last-played time, and location; clicking **Resume**
   opens the play surface with the full prior narrative already rendered (FR-006).

## Scenario 2 — Continue with nothing to continue (User Story 1, FR-002)

1. As a player with no sessions, `GET /api/game/sessions`. **Expect**: 200,
   `sessions: []` — a success, not a 404.
2. In the browser, open the stories screen (`/game`) as that player. **Expect**: a clear "nothing to continue"
   message where the list would be, with the "Choose an adventure" section still fully
   usable — no empty box and no error state (spec US1 Acceptance Scenario 3).

## Scenario 3 — Explicit save and return to the stories screen (User Story 2, FR-003)

1. With an active session, `POST /api/game/sessions/{sessionId}/checkpoints`.
   **Expect**: 201 with `checkpoint.label` equal to the latest turn's `locationLabel`, a
   `turnNumber` matching that turn, and a `createdAt` timestamp.
2. `GET /api/game/sessions/{sessionId}`. **Expect**: `checkpoints` has one entry;
   `turns`, `status`, and `lastInteractionAt` are **unchanged** from before step 1 — a save
   is not a turn (FR-003a).
3. Repeat step 1 immediately, with no interaction in between. **Expect**: 201 again, and
   `checkpoints` now holds two entries with the same `turnNumber` — the no-op save is kept,
   not de-duplicated (spec Edge Case 3).
4. In the browser, on the play surface, click **Save a checkpoint**. **Expect**: a brief
   visible confirmation naming the location ("Checkpoint saved at …") that dismisses itself
   after a few seconds, the story pane unchanged, and the input still usable.
5. Click **Pause & exit**, then **Save and exit to my stories**. **Expect**: a checkpoint is
   recorded and the player lands back on the stories screen (`/game`) with the game still
   listed under "Stories in progress" (FR-003).

## Scenario 4 — Resume never rewinds (FR-003a, FR-006)

1. Record a checkpoint (Scenario 3 step 1), then submit two more interactions.
2. Leave the game and resume it from the continue list.
   **Expect**: play continues from the **latest** turn, not from the checkpointed turn; the
   two post-checkpoint turns are present in the story pane and nothing was discarded.

## Scenario 5 — Sign out with a save accepted (User Story 2, FR-005)

1. In the browser, with an active game, navigate to a screen carrying the nav bar (`/menu` —
   the sign-out control is not present on the play surface or on `/game`) and
   click **Sign out**. **Expect**: a prompt asking whether to save first, stating that
   progress is already safe (FR-004).
2. Choose to save. **Expect**: a checkpoint is recorded and the sign-out completes.
3. Sign back in and resume that game from the continue list. **Expect**: every turn played
   before signing out is present, and `checkpoints` includes the marker from step 2
   (spec US2 Acceptance Scenario 3).

## Scenario 6 — Sign out with the save declined (User Story 2, FR-005)

1. Repeat Scenario 5 step 1, then decline the save.
2. **Expect**: the sign-out completes with no checkpoint recorded.
3. Sign back in and resume. **Expect**: **every turn is still present** — declining loses
   nothing; the only difference from Scenario 5 is that `checkpoints` gained no marker
   (spec US2 Acceptance Scenario 4).

## Scenario 7 — Sign out with no game in progress (FR-004)

1. As a player whose only session has concluded (play a short-duration adventure to its
   end), click **Sign out**. **Expect**: **no** prompt — sign-out proceeds directly
   (spec US2 Acceptance Scenario 5, spec Edge Case 2).
2. `POST /api/game/sessions/{concluded sessionId}/checkpoints`. **Expect**: 409
   `session_concluded`.
3. As a player with no sessions at all, click **Sign out**. **Expect**: no prompt.

## Scenario 8 — Switching between two in-progress games (FR-001a, spec Edge Case 5)

1. As player A, create a session on adventure X (`S1`), then one on adventure Y (`S2`).
   `008` makes `S2` the active one.
2. `GET /api/game/sessions`. **Expect**: two rows, `S2` first (most recent activity), with
   `isActiveForPlayer: true` on `S2` and `false` on `S1`; the UI marks `S2` as the current
   game.
3. In the browser, click **Resume** on `S1`. **Expect**: no confirmation dialog; `S1` opens
   playable and accepts an interaction immediately (no `409 session_inactive`).
4. `GET /api/game/sessions`. **Expect**: `S1` now reports `isActiveForPlayer: true` and
   `S2` `false`, with `S2`'s turns unchanged.
5. Click **Resume** on `S1` again while it is already the active game. **Expect**: it simply
   opens — no error shown, and no other game is set aside.

## Scenario 9 — A checkpoint that fails never traps the player (FR-006a)

1. With the backend's checkpoint write forced to fail (e.g. point the client at a stubbed
   503 `checkpoint_unavailable`, or take the container offline), click **Save a checkpoint**
   on the play surface. **Expect**: a notice saying the checkpoint could not be recorded
   **and that progress is safe**; the game remains playable.
2. Repeat via **Pause & exit → Save and exit to my stories**. **Expect**: the same notice,
   and the player still lands on the stories screen — the exit is not blocked or reversed.
3. Repeat via the sign-out prompt's save option. **Expect**: the notice renders and the
   sign-out still completes — no confirmation step, no retry gate (spec Edge Case 1).
4. Resume the game afterwards. **Expect**: all turns intact; only the marker is missing.

## Running the automated test suite

```bash
cd src/backend
pytest tests/unit/test_models.py \
       tests/unit/test_play_session_service.py \
       tests/integration/test_game_sessions_endpoint.py \
       tests/integration/test_saved_games_endpoint.py -v
```

```bash
cd src/frontend
npm test -- tests/Play tests/components/GameSetup tests/components/NavBar.test.jsx \
            tests/components/TitleBar.test.jsx tests/integration/save_and_continue.test.jsx
```

(See `tasks.md` for the tasks that create/extend each of these files; this quickstart's
nine scenarios map onto that suite's test cases per Constitution Principle I and FR-007.)
